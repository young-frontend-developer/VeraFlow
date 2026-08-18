# VeraFlow

VeraFlow helps people learn to recite the Qur'an correctly. It listens to a
recitation, detects pronunciation and Tajweed errors, highlights the mistake in
the text, and explains the correction — in Uzbek or Russian.

You pick an ayah, recite it, and get named tajweed mistakes with a fix and a
drill, in your own language.



## Run locally

```bash
# api
cd api
python -m venv .venv && source .venv/bin/activate   # Python 3.13
pip install -r requirements.txt
cp .env.example .env
uvicorn tilawah.api.main:app --reload --port 8000

# web
cd web
npm install
cp .env.example .env
npm run dev
```

The model (~1.3 GB) downloads on the first recitation, not at startup.

## How the engine works


1. **Quality gate first.** Below ~35 dB SNR the model hallucinates confidently. Reject before inference.
2. **Target is computed, not predicted.** Learner picked the ayah — correct phoneme sequence is deterministic.
3. **Typed errors, never a score.** Each error maps to one rule, one fix, one drill.
4. **Content is authored, not generated.** Every tajweed sentence lives in `api/tilawah/content/rules.json`.

## Deploy

```bash
docker compose up -d --build
```

## Before launch

- [ ] **Remove the DEV OVERRIDE** — `pytest` stays red until you do
- [ ] Qualified qori reviews every string in `rules.json`, then flip `reviewed`
- [ ] A **verified reciter** records the correct-recitation set — you cannot be
      your own ground truth (see `docs/`)
- [ ] Consent copy in uz/ru, and confirm `POST /api/consent` with `false`
      actually deletes
- [ ] Privacy policy — you are storing recitations of the Quran by named people

## What is deliberately not here

Lessons, exercises, Hifz scheduling, LLM phrasing, other riwayat, whole-Quran
coverage, real accounts, payments.

The typed error profile is the spine; all of those derive from it. Ship the loop,
