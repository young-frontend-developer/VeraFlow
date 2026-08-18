# VeraFlow

**[veraflow.uz](https://veraflow.uz)** — AI-powered Quran recitation coach for Uzbek and Russian speakers.

You pick an ayah, recite it, and get named tajweed mistakes with a fix and a drill — in your language.

```
VeraFlow/
  api/      FastAPI + tajweed engine
  web/      Vite + React PWA
  docs/     tajweed-engine-derisking.md
```

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

```
audio → decode → QUALITY GATE → computed target → model → typed errors → content
                      │              (deterministic)                        │
                      └── reject before inference              pre-authored uz/ru
```

1. **Quality gate first.** Below ~35 dB SNR the model hallucinates confidently. Reject before inference.
2. **Target is computed, not predicted.** Learner picked the ayah — correct phoneme sequence is deterministic.
3. **Typed errors, never a score.** Each error maps to one rule, one fix, one drill.
4. **Content is authored, not generated.** Every tajweed sentence lives in `api/tilawah/content/rules.json`.

## Deploy

```bash
docker compose up -d --build
```

## Before launch

- [ ] Remove DEV OVERRIDE — `pytest` stays red until you do
- [ ] Qualified qori reviews every string in `rules.json`
- [ ] Verified reciter records correct-recitation set
- [ ] Consent copy in uz/ru
- [ ] Privacy policy
