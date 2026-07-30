# -*- coding: utf-8 -*-
"""Settings from environment. See .env.example."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    model_id: str = os.getenv("TILAWAH_MODEL_ID", "obadx/muaalem-model-v3_2")
    model_device: str = os.getenv("TILAWAH_MODEL_DEVICE", "cpu")
    # bfloat16 halves the model to ~1.3 GB. Verify parity on your ayat before
    # trusting it in production - the spike only measured float32 end to end.
    model_dtype: str = os.getenv("TILAWAH_MODEL_DTYPE", "bfloat16")

    database_url: str = os.getenv("TILAWAH_DATABASE_URL", "sqlite:///./tilawah.db")
    cors_origins: str = os.getenv("TILAWAH_CORS_ORIGINS", "http://localhost:5173")

    max_upload_bytes: int = int(os.getenv("TILAWAH_MAX_UPLOAD_BYTES", 6_000_000))
    store_audio: bool = os.getenv("TILAWAH_STORE_AUDIO", "0") == "1"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
