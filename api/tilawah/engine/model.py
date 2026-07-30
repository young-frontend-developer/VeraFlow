# -*- coding: utf-8 -*-
"""Muaalem model wrapper - one instance per process.

2.42 GB in float32, ~1.3 GB in bfloat16. Loaded lazily so tests, migrations and
`--help` never pay for it. A semaphore of 1 serialises inference: CTC is a single
forward pass (decision 8), so one worker handles MVP traffic and two would just
double the memory.

Upgrade path when you outgrow it: move this module behind a queue (Redis + a
worker process) and keep the analyze() signature unchanged.
"""
import threading
from dataclasses import dataclass

import numpy as np
import torch

from ..config import settings

_lock = threading.Lock()
_infer = threading.Semaphore(1)
_model = None


@dataclass
class Prediction:
    phonemes: str
    sifat: list          # list[dict] - plain types, see spike/s3_transcribe.py
    mean_prob: float


def _label(u):
    return None if u is None else getattr(u, "text", str(u))


def _sifa_to_dict(s) -> dict:
    """quran_muaalem.Sifa -> plain dict.

    Its fields are SingleUnit(text, prob, idx) dataclasses, not strings, and the
    group is under `phonemes_group` (the reference side calls it `phonemes`).
    Both are flattened to label strings with confidence kept alongside.
    """
    fields = ["hams_or_jahr", "shidda_or_rakhawa", "tafkheem_or_taqeeq", "itbaq",
              "safeer", "qalqla", "tikraar", "tafashie", "istitala", "ghonna"]
    group = getattr(s, "phonemes", None) or getattr(s, "phonemes_group", None)
    d = {"phonemes": group if isinstance(group, str) else _label(group)}
    probs = {}
    for f in fields:
        v = getattr(s, f, None)
        if v is None or isinstance(v, str):
            d[f] = v
            continue
        d[f] = _label(v)
        p = getattr(v, "prob", None)
        if p is not None:
            probs[f] = round(float(p), 4)
    if probs:
        d["probs"] = probs
    return d


def get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from quran_muaalem import Muaalem
                dtype = torch.bfloat16 if settings.model_dtype == "bfloat16" else torch.float32
                _model = Muaalem(model_name_or_path=settings.model_id,
                                 device=settings.model_device, dtype=dtype)
    return _model


def transcribe(wave: np.ndarray, phonetized) -> Prediction:
    """One recitation -> predicted phonemes + sifat."""
    model = get_model()
    with _infer:
        out = model([wave], [phonetized], sampling_rate=16000)[0]

    probs = getattr(out.phonemes, "probs", None)
    if isinstance(probs, torch.Tensor):
        vals = probs.detach().cpu().float().reshape(-1).tolist()
    else:
        vals = list(probs or [])
    return Prediction(
        phonemes=_label(out.phonemes),
        sifat=[_sifa_to_dict(s) for s in (getattr(out, "sifat", None) or [])],
        mean_prob=float(sum(vals) / len(vals)) if vals else 0.0,
    )
