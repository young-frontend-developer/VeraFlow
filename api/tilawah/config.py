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

    # 16 kHz 16-bit mono PCM is 32 KB/s, and the longest ayah recited slowly is
    # ~248 s => ~7.9 MB. The old 6 MB ceiling predates whole-ayah practice and
    # would truncate the longest ayat; 12 MB clears the worst case with room to
    # spare. The recorder downsamples to 16 kHz before upload, so this is a
    # bound on duration and not on whatever rate the browser felt like using.
    max_upload_bytes: int = int(os.getenv("TILAWAH_MAX_UPLOAD_BYTES", 12_000_000))

    # The longest recitation the engine will attempt, in seconds.
    #
    # THIS IS A MEMORY LIMIT, NOT A TASTE ONE, and it is quadratic. wav2vec2-BERT
    # relative-position attention allocates a [frames, frames, 64] float32
    # tensor, and the model runs at 47 frames/s:
    #
    #     bytes = (47 * seconds)^2 * 256
    #
    #      52 s ->  1.5 GB   measured OK   (522 s wall, ~10x realtime)
    #      90 s ->  4.6 GB   the default below
    #     129 s ->  9.4 GB   measured FAILURE - DefaultCPUAllocator OOM on 8 GB
    #
    # 90 s covers 99.0% of the Quran recited whole at the slow-reciter rate; the
    # remaining 60 ayat need the "practise part of this ayah" control. Raise it
    # on a box with more RAM - the formula above is how to size it, and the
    # engine degrades to a clean retry rather than a 500 if it is set too high.
    max_audio_seconds: float = float(os.getenv("TILAWAH_MAX_AUDIO_SECONDS", 90))

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

    @property
    def show_unreviewed(self) -> bool:
        """Whether unreviewed corrections reach the screen, marked as drafts.

        DERIVED FROM THE ENVIRONMENT, not from its own flag. It used to be
        TILAWAH_SHOW_UNREVIEWED, defaulting off - which meant the default build
        showed a learner only the codes a qori had signed off. With 2 of 11
        authored codes reviewed, that was almost nothing: three real mistakes
        surfaced as one, or as "we couldn't fully assess". The gate was not
        protecting anyone, it was hiding the product from the person building
        it, and an opt-in flag is the wrong shape for something you want on
        every single development run.

        So the polarity is inverted and the flag is gone. Drafts show by default
        and the gate closes only in production, where the safety property that
        matters - no unreviewed ruling about the Quran presented as settled -
        is now structural rather than one unset variable away from failing.

        Everything unreviewed still travels marked `draft`, and the client must
        render that marker; see pipeline.present().
        """
        return not self.is_production


settings = Settings()
