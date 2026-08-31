# LinkedIn Profile API

A small FastAPI service that accepts a LinkedIn public profile URL and returns the profile data visible to the authenticated LinkedIn account as structured JSON. It sends direct HTTP requests to LinkedIn's authenticated Voyager (`/voyager/api`) endpoint; it does not use browser automation or third-party scraping services.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env`.
4. Set the following values from an authenticated LinkedIn session cookie:

   ```env
   LINKEDIN_LI_AT=your_li_at_cookie
   LINKEDIN_JSESSIONID="ajax:your_jsessionid"
   ```

   Keep the quotes around `LINKEDIN_JSESSIONID` if they are present in the cookie value. `.env` is ignored by Git.

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For local development, add `--reload`. Deploy behind an HTTPS-capable platform or reverse proxy, and keep both environment variables configured as secrets.

## API

`POST /profile`

```bash
curl -X POST http://localhost:8000/profile \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.linkedin.com/in/example/"}'
```

Example response:

```json
{
  "name": "Example Person",
  "headline": "Software Engineer",
  "location": "Bengaluru, Karnataka, India",
  "about": "...",
  "profile_image": "https://media.licdn.com/...",
  "experience": [{"title":"Engineer","company":"Example Co","location":"Bengaluru","description":"","start_date":"2024-01","end_date":""}],
  "education": [],
  "skills": ["Python"],
  "certifications": [],
  "languages": []
}
```

## Approach

The service extracts the `/in/<profile-id>` identifier, calls LinkedIn's internal authenticated `identity/profiles/{profile-id}/profileView` Voyager endpoint with the `li_at` and `JSESSIONID` cookies, then normalizes its returned profile and included entities into a stable response shape. Invalid URLs return `422`; missing or inaccessible profiles return `404`; rejected credentials return `401`; upstream/network failures return `502`.

## Known limitations

- LinkedIn's internal endpoints and response shape are undocumented and can change without notice.
- Results are limited to what the supplied account can view. Private or restricted profiles may return 404.
- Session cookies expire and must be refreshed manually.
- Use only in accordance with LinkedIn's terms, applicable law, and the permission of the people whose data you access.
