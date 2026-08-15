# VeyraFlow

VeyraFlow helps people learn to recite the Qur'an correctly. It listens to a
recitation, detects pronunciation and Tajweed errors, highlights the mistake in
the text, and explains the correction — in Uzbek or Russian.

You pick an ayah, recite it, and get at most two named mistakes with a fix and a
drill, in your own language.

Not a score. Not a teacher replacement.

```
VeyraFlow/
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

### The gate is on `TILAWAH_ENV`, and it is open in dev

`dev` renders **every** detected error — unreviewed codes and codes with no
authored text included, uncapped — each marked `draft` on the wire and shown
with a DRAFT chip. `production` shows only what a qori has reviewed.

It used to be an opt-in `TILAWAH_SHOW_UNREVIEWED`, defaulting off, which meant
the default build showed only the 2 of 11 authored codes that were signed off:
a learner making three mistakes saw one, or none. The flag is gone; the safety
property now follows the environment rather than a variable someone has to
remember. There is also no display cap — five errors found is five errors
shown, ranked by severity.

### Three answers, three sentences

| flag | means | UI says |
|---|---|---|
| `clean` | nothing was detected | praise |
| `suppressed` | detected, and the production gate withheld it | "izoh hali tayyor emas" |
| `analysable: false` | the model returned nothing to judge | "toʻliq baholay olmadik" |

They are mutually exclusive. The last two printed the *same* sentence once, so
a content-gate decision and a model failure were indistinguishable — on screen
and in a bug report. Telling someone their recitation was perfect when the
engine flagged it is the trust failure in the other direction, so `clean` never
covers for either.

### The practice range is the whole ayah

`GET /api/segments/{sura}/{aya}` returns `whole` plus an optional `parts` list;
the client selects `whole` and offers `parts` as a "practise part of this ayah"
control. Segmentation used to force the split on 4513 of 6236 ayat, which also
broke reciter playback — everyayah serves whole-ayah files only, so a fragment
had no audio to play.

**There is a measured ceiling, and it is memory, not taste.** wav2vec2-BERT
relative-position attention allocates a `[frames, frames, 64]` float32 tensor at
47 frames/s, so cost is quadratic in length. On this stack (8 GB, float32 CPU):

| audio | wall clock | ×realtime | outcome |
|---|---|---|---|
| 13 s | 18 s | 1.4× | ok |
| 52 s | 522 s | 10.0× | ok — 3 errors on an expert recitation |
| 129 s | — | — | **OOM**, tried to allocate 9.4 GB |

`TILAWAH_MAX_AUDIO_SECONDS` defaults to **90 s**, which covers **99.0%** of the
Quran recited whole at the slow-reciter rate. The 60 ayat above it warn *before*
recording — at ~10× realtime, finding out afterwards costs minutes — and are
practised through `parts`. An OOM that slips past the ceiling degrades to
`retry_recording / too_long_for_engine`, never a 500.

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
