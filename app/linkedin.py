"""Small client for LinkedIn's authenticated Voyager profile endpoint."""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import unquote, urlparse

import httpx


class LinkedInError(Exception):
    """Base error raised by the LinkedIn client."""


class InvalidLinkedInURL(LinkedInError):
    pass


class ProfileNotFound(LinkedInError):
    pass


class InvalidLinkedInSession(LinkedInError):
    pass


class LinkedInRequestFailed(LinkedInError):
    pass


PROFILE_URL_PATTERN = re.compile(r"^/in/([^/?#]+)/?$")
VOYAGER_BASE_URL = "https://www.linkedin.com/voyager/api"
PROFILE_DECORATION = "com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-101"
AUTH_REDIRECT_MESSAGE = (
    "LinkedIn redirected the request to sign-in or a checkpoint. "
    "Refresh LINKEDIN_LI_AT and LINKEDIN_JSESSIONID."
)


def extract_profile_identifier(profile_url: str) -> str:
    """Return the public profile identifier from a linkedin.com/in/... URL."""
    parsed = urlparse(profile_url.strip())
    hostname = (parsed.hostname or "").lower()

    if parsed.scheme not in {"http", "https"} or hostname not in {
        "linkedin.com",
        "www.linkedin.com",
        "m.linkedin.com",
    }:
        raise InvalidLinkedInURL("URL must be a LinkedIn profile URL (https://www.linkedin.com/in/<id>/).")

    match = PROFILE_URL_PATTERN.match(parsed.path)
    if not match:
        raise InvalidLinkedInURL("URL must point to a LinkedIn public profile under /in/.")

    return unquote(match.group(1))


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("text") or value.get("name") or "")
    return ""


def _first_string(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _image_url(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    if value.get("rootUrl") and value.get("artifacts"):
        artifacts = value["artifacts"]
        if isinstance(artifacts, list) and artifacts:
            segment = artifacts[-1].get("fileIdentifyingUrlPathSegment", "")
            return f"{value['rootUrl']}{segment}"
    return _first_string(value.get("url"), value.get("originalImage"))


def _date(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    year = value.get("year")
    month = value.get("month")
    day = value.get("day")
    if not year:
        return ""
    if day:
        return f"{year}-{int(month or 1):02d}-{int(day):02d}"
    if month:
        return f"{year}-{int(month):02d}"
    return str(year)


def _entity_name(item: dict[str, Any]) -> str:
    return _first_string(item.get("name"), item.get("title"), item.get("schoolName"), item.get("companyName"))


def _as_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _flatten_positions(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return individual positions when Voyager returns grouped positions."""
    positions: list[dict[str, Any]] = []
    for group in groups:
        nested = _as_list(group.get("profilePositionInPositionGroup")) or _as_list(group.get("positions"))
        if nested:
            positions.extend(nested)
        else:
            positions.append(group)
    return positions


def normalize_profile(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize Voyager profileView JSON into a stable, documented shape."""
    # The endpoint can return its body directly or within a `data` object.
    body = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    included = [*_as_list(payload.get("included")), *_as_list(body.get("included"))]
    profile = body.get("profile") if isinstance(body.get("profile"), dict) else next(
        (item for item in included if "firstName" in item and "Profile" in str(item.get("$type", ""))),
        body,
    )

    # Profile-view responses vary by account and LinkedIn experiment. Merge the
    # top-level collections with included entities and use their $type when present.
    all_entities = [*included]
    for key in ("positionGroup", "education", "skill", "certification", "language"):
        all_entities.extend(_as_list(body.get(key)))

    position_groups = _as_list(body.get("positionGroup")) or [
        item for item in all_entities if "Position" in str(item.get("$type", ""))
    ]
    positions = _flatten_positions(position_groups)
    education = _as_list(body.get("education")) or [
        item for item in all_entities if "Education" in str(item.get("$type", ""))
    ]
    skills = _as_list(body.get("skill")) or [
        item for item in all_entities if "Skill" in str(item.get("$type", ""))
    ]
    certifications = _as_list(body.get("certification")) or [
        item for item in all_entities if "Certification" in str(item.get("$type", ""))
    ]
    languages = _as_list(body.get("language")) or [
        item for item in all_entities if "Language" in str(item.get("$type", ""))
    ]

    return {
        "name": " ".join(part for part in [profile.get("firstName", ""), profile.get("lastName", "")] if part).strip()
        or _first_string(profile.get("name")),
        "headline": _first_string(profile.get("headline")),
        "location": _first_string(profile.get("locationName"), profile.get("geoLocationName")),
        "about": _first_string(profile.get("summary"), profile.get("about")),
        "profile_image": _image_url(
            profile.get("profilePicture") or profile.get("picture") or profile.get("displayPictureUrl")
        ),
        "experience": [
            {
                "title": _first_string(item.get("title")),
                "company": _first_string(item.get("companyName"), item.get("company", {}).get("name") if isinstance(item.get("company"), dict) else ""),
                "location": _first_string(item.get("locationName")),
                "description": _first_string(item.get("description")),
                "start_date": _date(item.get("timePeriod", {}).get("startDate") if isinstance(item.get("timePeriod"), dict) else item.get("startDate")),
                "end_date": _date(item.get("timePeriod", {}).get("endDate") if isinstance(item.get("timePeriod"), dict) else item.get("endDate")),
            }
            for item in positions
            if _entity_name(item)
        ],
        "education": [
            {
                "school": _first_string(item.get("schoolName"), item.get("school", {}).get("name") if isinstance(item.get("school"), dict) else ""),
                "degree": _first_string(item.get("degreeName")),
                "field_of_study": _first_string(item.get("fieldOfStudy")),
                "start_date": _date(item.get("timePeriod", {}).get("startDate") if isinstance(item.get("timePeriod"), dict) else item.get("startDate")),
                "end_date": _date(item.get("timePeriod", {}).get("endDate") if isinstance(item.get("timePeriod"), dict) else item.get("endDate")),
            }
            for item in education
            if _entity_name(item)
        ],
        "skills": [name for item in skills if (name := _entity_name(item))],
        "certifications": [
            {
                "name": _first_string(item.get("name")),
                "issuer": _first_string(item.get("authority"), item.get("companyName")),
                "issue_date": _date(item.get("timePeriod", {}).get("startDate") if isinstance(item.get("timePeriod"), dict) else item.get("issueDate")),
                "expiration_date": _date(item.get("timePeriod", {}).get("endDate") if isinstance(item.get("timePeriod"), dict) else item.get("expirationDate")),
                "credential_id": _first_string(item.get("licenseNumber"), item.get("credentialId")),
                "credential_url": _first_string(item.get("url")),
            }
            for item in certifications
            if _entity_name(item)
        ],
        "languages": [
            {
                "name": _first_string(item.get("name")),
                "proficiency": _first_string(item.get("proficiency"), item.get("proficiencyLevel")),
            }
            for item in languages
            if _entity_name(item)
        ],
    }


class LinkedInClient:
    def __init__(self, li_at: str | None = None, jsessionid: str | None = None) -> None:
        self.li_at = li_at or os.getenv("LINKEDIN_LI_AT")
        self.jsessionid = jsessionid or os.getenv("LINKEDIN_JSESSIONID")
        if not self.li_at or not self.jsessionid:
            raise InvalidLinkedInSession("LINKEDIN_LI_AT and LINKEDIN_JSESSIONID must be set.")

    async def get_profile(self, profile_url: str) -> dict[str, Any]:
        identifier = extract_profile_identifier(profile_url)
        csrf_token = self.jsessionid.strip('"')
        headers = {
            "accept": "application/vnd.linkedin.normalized+json+2.1",
            "accept-language": "en-US,en;q=0.9",
            "csrf-token": csrf_token,
            "referer": f"https://www.linkedin.com/in/{identifier}/",
            "x-li-lang": "en_US",
            "x-restli-protocol-version": "2.0.0",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        }
        cookies = {"li_at": self.li_at, "JSESSIONID": self.jsessionid}
        dash_endpoint = f"{VOYAGER_BASE_URL}/identity/dash/profiles"
        legacy_endpoint = f"{VOYAGER_BASE_URL}/identity/profiles/{identifier}/profileView"
        params = {
            "q": "memberIdentity",
            "memberIdentity": identifier,
            "decorationId": PROFILE_DECORATION,
        }

        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
                response = await client.get(dash_endpoint, params=params, headers=headers, cookies=cookies)
                # Keep the old endpoint only for LinkedIn accounts that have not
                # yet migrated to the Dash profile API, or profiles that are not
                # exposed through the account's current Dash experiment.
                if response.status_code in {404, 410}:
                    response = await client.get(legacy_endpoint, headers=headers, cookies=cookies)
        except httpx.RequestError as exc:
            raise LinkedInRequestFailed("Unable to reach LinkedIn.") from exc

        if response.is_redirect:
            raise InvalidLinkedInSession(AUTH_REDIRECT_MESSAGE)
        if response.status_code in {401, 403}:
            raise InvalidLinkedInSession("LinkedIn rejected the supplied session credentials.")
        if response.status_code == 404:
            raise ProfileNotFound("LinkedIn profile was not found or is not visible to this account.")
        if response.status_code >= 400:
            raise LinkedInRequestFailed(f"LinkedIn request failed with status {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise LinkedInRequestFailed("LinkedIn returned an unexpected response.") from exc
        if not isinstance(payload, dict):
            raise LinkedInRequestFailed("LinkedIn returned an unexpected response.")
        return normalize_profile(payload)
