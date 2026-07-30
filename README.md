# Tilawah

Tajweed feedback for Uzbek and Russian speakers. You pick an ayah, recite it, and
get at most two named mistakes with a fix and a drill — in your own language.

Not a score. Not a teacher replacement.

```
Tilawah/
  api/      FastAPI + the tajweed engine
  web/      Vite + React PWA
  spike/    the de-risking spike (frozen — do not build on it)
  docs/     tajweed-engine-derisking.md
```

## Run it

```bash
# api
cd api
python -m venv .venv && .venv/Scripts/activate      # Python 3.13, NOT 3.14
pip install -r requirements.txt
cp .env.example .env
uvicorn tilawah.api.main:app --reload --port 8010     # http://localhost:8010/docs

# web
cd web
npm install
cp .env.example .env
npm run dev                                          # http://localhost:5173
```

The model (~1.3 GB in bfloat16) downloads on the first recitation, not at
startup. Expect ~15 s once, then ~2-4 s per attempt on CPU.

```bash
cd api && pytest -q     # 16 pass + 1 intentional failure (see DEV OVERRIDE), no model load
```

## How the engine works

```
audio ──► decode ──► QUALITY GATE ──► computed target ──► model ──► typed errors ──► content
                          │                (deterministic)                              │
                          └── reject before inference                    pre-authored uz/ru
```

1. **Quality gate first.** Below ~35 dB SNR the model does not degrade
   gracefully — it snaps to huruf muqatta'at at 0.9+ confidence. Confident,
   fluent nonsense. Reject the take and ask for another *before* inference.
2. **The target is computed, not predicted.** The learner picked the ayah, so
   the correct phoneme sequence is deterministic from Uthmani text + riwayah.
   This is diff-against-known-target, not speech-to-text.
3. **Run-length decode before diffing.** QPS encodes duration as repeated
   characters, so a shortened madd and a dropped letter look identical to a raw
   character diff. Collapsing runs into `(letter, count)` separates them.
4. **Typed errors, never a score.** Each error maps to one rule, one fix, one
   drill.
5. **Content is authored, not generated.** Every sentence about tajweed lives in
   `api/tilawah/content/rules.json`. No LLM writes any of it.

## The two safety gates

**`status`** in `rules.json` — per-error-type, no code change:

| | |
|---|---|
| `ship` | shown normally; has a measured false-positive rate |
| `teacher` | shown, ends with "check with your teacher" |
| `collect` | logged in `silent_errors`, **never shown** |

New error types start at `collect`. Promote one only when you have its
false-positive rate on correct recitation from a **verified** reciter.

**`reviewed`** in `rules.json` — unreviewed strings never reach a learner,
whatever their `status`. **Get a qualified qori to review the uz/ru strings
before launch** — the Uzbek and Russian in `rules.json` is a first draft written
by a developer, not a scholar.

### ⚠ DEV OVERRIDE IS CURRENTLY ACTIVE

`SUB_AYN_HAMZA` and `SUB_SAD_SEEN` are flipped to `status: ship` +
`reviewed: true` **so the app can be demonstrated**. No qori has seen those
strings. This is not fit to launch.

Three things will not let you forget:

| | |
|---|---|
| `rules.json` | each override carries `reviewed_by: "DEV-OVERRIDE …"`, and `_meta.DEV_OVERRIDE` names them |
| API startup | logs a `DEV OVERRIDE ACTIVE — NOT FIT TO LAUNCH` banner every boot |
| `pytest` | `test_no_dev_overrides_remain` **fails on purpose** and names the codes |

That test failure is the one red the suite is allowed to have — anything else
going red is a real regression. To re-gate: set `reviewed: false` and drop
`reviewed_by`, or replace it with the name of the qori who signed off.

```bash
grep -rn "DEV-OVERRIDE" api/tilawah/content/rules.json   # find every one
```

### Praise is gated too

`clean` means *nothing was detected*. If something was detected but suppressed,
the response sets `suppressed` and the UI says "couldn't fully assess — check
with your teacher". Telling someone their recitation was perfect when the engine
flagged it is a trust failure in the other direction.

## Deploy

```bash
docker compose up -d --build      # one box, one worker
```

Hetzner CX32 (4 vCPU / 8 GB, ~€7/mo) is enough. One worker on purpose — each
loads its own copy of the model. When one box stops being enough, put
`engine/model.py` behind a queue and keep `analyze()` unchanged.

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
get real attempts, then build the rest on evidence.
