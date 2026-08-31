# LinkedIn Profile API

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](./Dockerfile)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#testing)

Fetch structured LinkedIn profile data through LinkedIn's authenticated Voyager REST API - no browser automation or DOM scraping.

| Resource | URL |
| --- | --- |
| Web demo | [linked-in-profile-api-livid.vercel.app](https://linked-in-profile-api-livid.vercel.app/) |
| Interactive API docs | [linkedin-profile-api-bsa2.onrender.com/docs](https://linkedin-profile-api-bsa2.onrender.com/docs) |
| Health check | [linkedin-profile-api-bsa2.onrender.com/health](https://linkedin-profile-api-bsa2.onrender.com/health) |

The Render free tier may need 30-60 seconds to wake up. Warm it before testing:

```bash
curl https://linkedin-profile-api-bsa2.onrender.com/health
# {"status":"ok"}
```

## Reviewer quick start

1. Open the [web demo](https://linked-in-profile-api-livid.vercel.app/).
2. Paste a LinkedIn profile URL or vanity slug.
3. Select **Fetch profile** to render the normalized result.

The hosted API uses server-side `LI_AT` and `JSESSIONID` credentials. LinkedIn can invalidate a session because of expiry, logout, or an IP change. If the hosted API returns `401 Unauthorized`, [run the API locally](#run-locally) with your own session values; no source changes or Vercel redeploy are needed.

Then point the deployed UI to the local API:

```text
https://linked-in-profile-api-livid.vercel.app/?api=http://localhost:8000
```

Credentials remain on the reviewer's machine and are never sent to the public demo API.

## What it returns

- Identity, headline, About summary, location, and LinkedIn profile URL
- High-resolution profile and cover image URLs
- Experience and education, including normalized date ranges
- Skills, certifications, languages, and featured/treasury media
- A UTC `fetched_at` timestamp
- Consistent HTTP error responses

## API reference

### Fetch a profile

| Method | Endpoint | Input |
| --- | --- | --- |
| `GET` | `/api/profile?url={value}` | LinkedIn profile URL or vanity slug |
| `POST` | `/api/profile` | `{"url": "https://www.linkedin.com/in/..."}` |

GET example:

```bash
curl "https://linkedin-profile-api-bsa2.onrender.com/api/profile?url=https://www.linkedin.com/in/shreyan-bagchi/"
```

POST example:

```bash
curl -X POST "https://linkedin-profile-api-bsa2.onrender.com/api/profile" \
  -H "Content-Type: application/json" \
  -d '{"url":"shreyan-bagchi"}'
```

Accepted inputs:

| Input | Normalized slug |
| --- | --- |
| `https://www.linkedin.com/in/shreyan-bagchi/` | `shreyan-bagchi` |
| `in.linkedin.com/in/shreyan-bagchi?trk=feed` | `shreyan-bagchi` |
| `linkedin.com/in/shreyan-bagchi` | `shreyan-bagchi` |
| `shreyan-bagchi` | `shreyan-bagchi` |

### Response

Abridged example from `response.json`:

```json
{
  "first_name": "Shreyan",
  "last_name": "Bagchi",
  "headline": "MTS@Oracle (OCI) || Backend Engineer || ...",
  "summary": "Software Engineer with experience at Oracle...",
  "public_identifier": "shreyan-bagchi",
  "profile_url": "https://www.linkedin.com/in/shreyan-bagchi/",
  "location": {
    "city": "Raurkela",
    "state": "Odisha",
    "country": "IN",
    "display": "Raurkela, Odisha, India"
  },
  "profile_picture_url": "https://media.licdn.com/dms/image/v2/...",
  "cover_picture_url": "https://media.licdn.com/dms/image/v2/...",
  "positions": [
    {
      "title": "Member of Technical Staff",
      "company_name": "Oracle",
      "location": "Bengaluru",
      "employment_type": "Full-time",
      "date_range": {
        "start_year": 2025,
        "start_month": 7,
        "is_current": false
      }
    }
  ],
  "educations": [
    {
      "school_name": "Indian Institute of Technology, Bhubaneswar",
      "degree_name": "Bachelor of Technology",
      "field_of_study": "Electrical and Electronics Engineering"
    }
  ],
  "skills": [
    { "name": "Java" },
    { "name": "Spring Boot" },
    { "name": "PostgreSQL" }
  ],
  "skills_total": 47,
  "treasury_media": [
    {
      "title": "strike07 - Codeforces",
      "url": "https://codeforces.com/profile/strike07",
      "kind": "url"
    }
  ],
  "fetched_at": "..."
}
```

When available, the response also includes `urn`, `certifications[]`, and `languages[]`.

### Errors

All application errors use this shape:

```json
{"error":"unauthorized","detail":"LinkedIn session expired or invalid","status":401}
```

| HTTP | Error code | Meaning |
| --- | --- | --- |
| `400` | `invalid_url` | The input is malformed or is not a LinkedIn profile URL/slug. |
| `401` | `unauthorized` | The LinkedIn session is expired or invalid. |
| `403` | `forbidden` | LinkedIn denied access to the profile. |
| `404` | `not_found` | The profile does not exist or is unavailable. |
| `429` | `rate_limit_exceeded` | The API or LinkedIn rate limit was reached. |
| `502` | `upstream_error` | LinkedIn returned a server or network error. |

### Health check

```http
GET /health
```

```json
{"status":"ok"}
```

## Run locally

### 1. Get LinkedIn session values

1. Sign in at [linkedin.com](https://www.linkedin.com/).
2. Open DevTools, then **Application > Cookies > https://www.linkedin.com**.
3. Copy `li_at` and `JSESSIONID`. Remove the surrounding quotes from `JSESSIONID` when adding it to `.env`.
4. Copy your browser's `User-Agent` value from a request in the Network panel.

Never commit these credentials.

### 2. Install and configure

Python 3.12 or newer is required.

```bash
python -m venv .venv
```

Activate the environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies and create the local environment file:

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

On Windows PowerShell, use `Copy-Item .env.example .env` instead of `cp` if needed. Fill in the three required values:

```dotenv
LI_AT=your_li_at_cookie_here
JSESSIONID=your_jsessionid_here
USER_AGENT=Mozilla/5.0 ...
```

### 3. Start the API

```bash
uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger UI.

### Docker

```bash
docker build -t linkedin-profile-api .
docker run -p 8000:8000 \
  -e LI_AT=... \
  -e JSESSIONID=... \
  -e USER_AGENT="Mozilla/5.0 ..." \
  linkedin-profile-api
```

## Configuration

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `LI_AT` | Yes | - | Authenticated LinkedIn session cookie |
| `JSESSIONID` | Yes | - | Session value used for the cookie and CSRF header |
| `USER_AGENT` | Yes | - | Browser user-agent string |
| `CACHE_TTL_SECONDS` | No | `3600` | In-memory profile cache lifetime |
| `RATE_LIMIT` | No | `10/minute` | Per-IP API rate limit |
| `LOG_LEVEL` | No | `INFO` | Application logging level |

## Architecture

```text
Client
  -> GET/POST /api/profile
  -> URL normalizer
  -> in-memory TTL cache
  -> async Voyager client (Rest.li 2.0, retries)
  -> included[] entity parser
  -> validated ProfileResponse
```

| Component | Responsibility |
| --- | --- |
| `url_normalizer` | Accept full LinkedIn URLs and vanity slugs, then validate and normalize them. |
| `voyager_client` | Send authenticated async requests with Rest.li headers and retry transient upstream failures. |
| `profile_parser` | Group `included[]` entities by `$type` and resolve vector artifacts to CDN image URLs. |
| `profile_service` | Coordinate normalization, caching, fetching, skills enrichment, and parsing. |

The primary upstream request is:

```http
GET /voyager/api/identity/dash/profiles
  ?q=memberIdentity
  &memberIdentity={slug}
  &decorationId=com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-91
```

Authentication follows LinkedIn's Rest.li double-submit cookie pattern: the `li_at` cookie authenticates the session, while the raw `JSESSIONID` value is sent as the `csrf-token` header.

## Why Voyager REST

LinkedIn's newer `/flagship-web/...` profile surfaces use Server-Driven UI/RSC Flight streams, which makes UI-tree parsing brittle. This service instead consumes the normalized entity graph returned by Voyager's `FullProfileWithEntities-91` decoration.

| | Headless browser | Direct Voyager REST |
| --- | --- | --- |
| Transport | Rendered DOM via Playwright/Puppeteer | Authenticated JSON over `httpx` |
| Typical latency | Browser startup plus page rendering | Usually under 300 ms for the core request |
| Main coupling | CSS selectors and DOM structure | `$type` entity schema and decoration ID |
| Challenge fit | Disallowed | Required approach |

The consolidated payload generally embeds the first skills page (about 20 items). The service attempts Voyager pagination when a larger total is reported, but the tested deep endpoints currently fail (`/profileSkills` with `400`, legacy `/skills` with `410`). In that case, it keeps the embedded page and exposes the full available count through `skills_total`.

## Production trade-offs

### Authentication model

The public API deliberately does not accept per-request `X-Li-At` or `X-JSessionID` headers. Sending a reviewer's personal LinkedIn session through a third-party host creates account-lock and unusual-IP risk.

Instead, the deployment reads one owner-controlled session from environment variables. If that session expires, reviewers can run the API locally so their cookies never leave their machine.

### Limitations

- **Session fragility:** `li_at` and `JSESSIONID` can expire or be invalidated after a logout or IP change.
- **Single-account limits:** one LinkedIn session backs the hosted traffic. The TTL cache and per-IP rate limiter reduce upstream load.
- **Skills pagination:** follow-up Voyager skills endpoints may be unavailable; partial results are returned safely when enrichment fails.
- **Schema drift:** LinkedIn can change `$type` names or decoration IDs. Update `app/config.py` if upstream responses change.
- **Profile visibility:** results are limited to profiles visible to the authenticated LinkedIn account.
- **Terms:** use the service responsibly and in accordance with LinkedIn's Terms of Service.

## Testing

```bash
pytest -v
```

The test suite covers URL normalization, response parsing, GET and POST routes, upstream error mapping, caching, and skills pagination fallbacks.

## License

MIT. Keep LinkedIn credentials in local environment files or host secrets only.
