import unittest
from unittest.mock import patch

import httpx

from app.linkedin import InvalidLinkedInSession, LinkedInClient, extract_profile_identifier


class FakeAsyncClient:
    def __init__(self, responses, calls):
        self.responses = iter(responses)
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)


class LinkedInURLTests(unittest.TestCase):
    def test_supported_profile_url_variants(self):
        urls = [
            "https://linkedin.com/in/example",
            "https://www.linkedin.com/in/example/",
            "http://m.linkedin.com/in/example?trk=public_profile",
            "https://www.linkedin.com/in/example/#about",
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(extract_profile_identifier(url), "example")


class LinkedInClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_identifier_from_any_profile_url(self):
        calls = []
        response = httpx.Response(
            200,
            json={"firstName": "Carol", "lastName": "Roy"},
            request=httpx.Request("GET", "https://www.linkedin.com/voyager/api/test"),
        )
        fake_client = FakeAsyncClient([response], calls)

        with patch("app.linkedin.httpx.AsyncClient", return_value=fake_client):
            profile = await LinkedInClient("li_at", '"ajax:csrf"').get_profile(
                "https://www.linkedin.com/in/carolroy1525/"
            )

        self.assertEqual(profile["name"], "Carol Roy")
        self.assertEqual(calls[0][1]["params"]["memberIdentity"], "carolroy1525")

    async def test_falls_back_to_legacy_endpoint(self):
        calls = []
        request = httpx.Request("GET", "https://www.linkedin.com/voyager/api/test")
        fake_client = FakeAsyncClient(
            [
                httpx.Response(410, request=request),
                httpx.Response(200, json={"firstName": "Example"}, request=request),
            ],
            calls,
        )

        with patch("app.linkedin.httpx.AsyncClient", return_value=fake_client):
            profile = await LinkedInClient("li_at", '"ajax:csrf"').get_profile(
                "https://linkedin.com/in/example"
            )

        self.assertEqual(profile["name"], "Example")
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[1][0].endswith("/identity/profiles/example/profileView"))

    async def test_redirect_is_reported_as_invalid_session(self):
        calls = []
        response = httpx.Response(
            302,
            headers={"location": "https://www.linkedin.com/login"},
            request=httpx.Request("GET", "https://www.linkedin.com/voyager/api/test"),
        )
        fake_client = FakeAsyncClient([response], calls)

        with patch("app.linkedin.httpx.AsyncClient", return_value=fake_client):
            with self.assertRaisesRegex(InvalidLinkedInSession, "sign-in or a checkpoint"):
                await LinkedInClient("li_at", '"ajax:csrf"').get_profile(
                    "https://www.linkedin.com/in/example/"
                )


if __name__ == "__main__":
    unittest.main()
