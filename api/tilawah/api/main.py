# -*- coding: utf-8 -*-
"""FastAPI app.

Run:  uvicorn tilawah.api.main:app --reload
Docs: http://localhost:8000/docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .. import content
from ..config import settings
from ..db import init_db
from .routes import router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()

    # DEV ONLY tripwire. Some rules are flipped to reviewed=true so the app can
    # be demonstrated before content review is finished. Say so on every boot,
    # loudly, so it cannot quietly reach a real user.
    overrides = content.dev_overrides()
    if overrides:
        bar = "!" * 68
        logging.warning(bar)
        logging.warning("DEV OVERRIDE ACTIVE - NOT FIT TO LAUNCH")
        logging.warning("Showing tajweed corrections NO QORI HAS REVIEWED: %s",
                        ", ".join(overrides))
        logging.warning("Re-gate in tilawah/content/rules.json before launch.")
        logging.warning(bar)

    # Refuse to serve real people while storing their voice without asking.
    if settings.debug_audio and settings.is_production:
        raise RuntimeError(
            "TILAWAH_DEBUG_AUDIO=1 stores every recording with NO consent. "
            "That is a laptop-only diagnostic. Unset it, or set TILAWAH_ENV=dev "
            "if this really is a development box."
        )
    if settings.debug_audio:
        logging.warning("=" * 68)
        logging.warning("DEBUG AUDIO ON - every upload is stored, consent IGNORED")
        logging.warning("Development only. Never set this where real learners can reach.")
        logging.warning("=" * 68)
    logging.info("audio retention: collect=%s (per-learner consent still required)",
                 settings.collect_audio)

    # The model is NOT preloaded. First recitation pays ~15 s; every later one
    # is fast. Preloading here would make deploys slow and health checks lie.
    logging.info("Tilawah API ready (model loads on first analyse, dtype=%s)",
                 settings.model_dtype)
    yield


app = FastAPI(title="Tilawah API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
