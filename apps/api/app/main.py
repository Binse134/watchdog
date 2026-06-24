import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.auth import router as auth_router
from app.config import settings
from app.connections import router as connections_router
from app.scheduler import run_check_cycle, start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="No-Code Watchdog API", lifespan=lifespan)

allow_origins = {"http://localhost:3000", settings.frontend_url.rstrip("/")}

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(connections_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/internal/check")
def trigger_check(x_internal_secret: str | None = Header(default=None)):
    """Lets an external cron service run a check cycle on demand, so checks
    still happen on platforms that spin the process down on idle (which
    would otherwise pause the in-process scheduler started in lifespan()).
    Disabled (404) unless INTERNAL_CHECK_SECRET is configured.
    """
    if not settings.internal_check_secret:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if not secrets.compare_digest(x_internal_secret or "", settings.internal_check_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    run_check_cycle()
    return {"ok": True}
