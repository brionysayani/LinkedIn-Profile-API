from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.linkedin import (
    InvalidLinkedInSession,
    InvalidLinkedInURL,
    LinkedInClient,
    LinkedInRequestFailed,
    ProfileNotFound,
)

load_dotenv()


class ProfileRequest(BaseModel):
    url: str


app = FastAPI(title="LinkedIn Profile API", version="1.0.0")
PUBLIC_DIR = Path(__file__).parent.parent / "public"


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(PUBLIC_DIR / "index.html")


@app.post("/profile")
async def profile(request: ProfileRequest):
    try:
        return await LinkedInClient().get_profile(request.url)
    except InvalidLinkedInURL as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ProfileNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidLinkedInSession as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except LinkedInRequestFailed as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
