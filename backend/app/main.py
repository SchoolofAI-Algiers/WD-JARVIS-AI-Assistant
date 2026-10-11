import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.api.routes import voice

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Load the speech voices in the background: the server accepts requests immediately and the first
    # spoken reply does not pay the model-loading time.
    task = asyncio.create_task(voice.warmup_voice_tts())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task


app = FastAPI(title="JARVIS API", lifespan=lifespan)
app.include_router(voice.router, prefix="/api/v1")

# Frontend development server
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}