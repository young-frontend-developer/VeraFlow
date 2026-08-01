# -*- coding: utf-8 -*-
"""Settings from environment. See .env.example."""
import os
from dataclasses import dataclass
from pathlib import Path

# Load api/.env before the field defaults below are evaluated. Without this the
# file is decorative: uvicorn only reads .env when you pass --env-file, so every
# value here silently fell back to its default no matter what the file said.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # dotenv rides along with uvicorn[standard]; don't hard-fail
    pass


@dataclass(frozen=True)
class Settings:
    model_id: str = os.getenv("TILAWAH_MODEL_ID", "obadx/muaalem-model-v3_2")
    model_device: str = os.getenv("TILAWAH_MODEL_DEVICE", "cpu")
    # float32, deliberately. bfloat16 halves the model to ~1.3 GB but there is
    # no native bf16 compute path on a typical x86 CPU, so torch emulates it by
    # upconverting every matmul. Measured on the same clip, same output:
    #
    #     float32   1.33 s   2.6 GB peak
    #     bfloat16 19.68 s   1.3 GB peak     <- 15x slower, identical phonemes
    #
    # Trading 1.3 GB of RAM for 15x latency is the wrong way round when memory
    # costs a few euros a month and latency is the practice loop.
    model_dtype: str = os.getenv("TILAWAH_MODEL_DTYPE", "float32")

    database_url: str = os.getenv("TILAWAH_DATABASE_URL", "sqlite:///./tilawah.db")
    cors_origins: str = os.getenv("TILAWAH_CORS_ORIGINS", "http://localhost:5173")

    max_upload_bytes: int = int(os.getenv("TILAWAH_MAX_UPLOAD_BYTES", 6_000_000))

    # Learner voice is never retained unless the learner asked for it to be.
    # This flag only permits the offer to be made; the per-user consent in
    # User.audio_consented is what actually authorises a write. Turning it off
    # disables audio retention for everyone regardless of what they consented to,
    # which is the switch you want if something goes wrong.
    collect_audio: bool = os.getenv("TILAWAH_COLLECT_AUDIO", "0") == "1"

    # OPERATOR DIAGNOSTIC MODE - stores every upload with NO consent at all.
    # For a laptop while debugging, never for a box real people can reach.
    # main.py refuses to start with this on unless TILAWAH_ENV=dev.
    debug_audio: bool = os.getenv("TILAWAH_DEBUG_AUDIO", "0") == "1"
    debug_dir: str = os.getenv("TILAWAH_DEBUG_DIR", "")

    # OPERATOR DIAGNOSTIC MODE - bypasses the content review gate entirely and
    # renders EVERY detected error, including codes no qori has reviewed and
    # codes with no authored content at all. Also lifts the two-error display
    # cap, because the point is to see everything the engine found.
    #
    # This exists so the engine can be inspected end to end without flipping
    # `reviewed` in rules.json - which is the one flag that must never be
    # loosened for convenience, since it is what keeps unreviewed rulings about
    # the Quran away from learners.
    #
    # main.py refuses to start with this on unless TILAWAH_ENV=dev, exactly like
    # debug_audio. Everything it surfaces is marked `draft` on the wire so the
    # client cannot render it as settled guidance even by accident.
    show_unreviewed: bool = os.getenv("TILAWAH_SHOW_UNREVIEWED", "0") == "1"

    env: str = os.getenv("TILAWAH_ENV", "dev")           # dev | production
    # Shows the "not yet fully verified" banner. Also raised automatically while
    # any learner-facing correction is unreviewed, so it cannot be forgotten.
    pilot: bool = os.getenv("TILAWAH_PILOT", "1") == "1"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env.lower() in ("production", "prod")


settings = Settings()
