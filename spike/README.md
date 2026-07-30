# Tilawah Spike — Runbook

**Goal:** get one number — *does the Muaalem model detect learner Tajweed errors reliably enough to build a product on?*

**Time:** ~2 weeks part-time. **Cost:** $0. **GPU:** not needed.

---

## Hardware verdict: your laptop is fine

I checked your machine:

| | |
|---|---|
| CPU | Intel i5-13420H — 8 cores / 12 threads |
| RAM | **7.7 GB total** ← the only constraint |
| GPU | Intel UHD (integrated, no CUDA) — **unused, doesn't matter** |
| Disk | 279 GB free — plenty |

**You do not need to rent a GPU.** Here's why: the model is an *encoder with a CTC head* — one forward pass, no token-by-token generation. That's the opposite of LLM inference economics. Rough arithmetic: ~660M params × ~200 audio frames ≈ 240 GFLOPs per clip, against maybe 150–300 GFLOPS usable on your CPU. **Expect ~1–3 seconds per clip.** All 150 clips run in under 10 minutes.

RAM is the real limit. The model is 2.42 GB on disk (float32), and PyTorch plus activations add ~1 GB. On a 7.7 GB machine that fits — **but close Chrome and everything else before running `s3`.** If you hit an out-of-memory error, `s3` has a `--dtype bfloat16` flag that halves the model's memory (~1.3 GB) at some cost in speed.

**Escape hatch if the laptop fights you:** Google Colab's free tier gives you a T4 GPU, and the model needs only ~1.5 GB of VRAM. Zero cost. Only reach for it if local runs fail.

---

## Step 0 — Ten minutes, zero install: sanity-check the model on your own voice

Before writing any code, go to a live demo and recite into it:

- <https://huggingface.co/spaces/ahmednsalehm/quran-muaalem-tajweed> — grades recitation with Tajweed feedback
- <https://huggingface.co/spaces/OsamaO/SpaceOfQuran-muaalem> — raw model output

Recite Sūrat al-ʿAṣr āyah 1 (`وَٱلْعَصْرِ`) three ways: correctly, then with ع read as a hamza, then with ص read as a plain س.

**If the demo doesn't visibly react to those two deliberate errors, stop and tell me** — that's Risk 1 from the architecture doc showing up immediately, and it changes the plan before you've spent two weeks. If it does react, continue.

---

## Step 1 — Install (one time, ~20 min mostly download)

> **Use Python 3.13, not 3.14.** You have both. PyTorch and `numba` don't have reliable 3.14 wheels yet, and you'll fight the installer for no reason. 3.13 is the boring correct choice.

Open PowerShell in the project folder:

```powershell
cd C:\Users\Rahmatulloh\Desktop\Tilawah\spike

# 1. Create an isolated environment on Python 3.13
py -3.13 -m venv .venv

# 2. Activate it  (do this in EVERY new terminal — prompt should show "(.venv)")
.\.venv\Scripts\Activate.ps1

# 3. Install everything (~2.5 GB of downloads, be patient)
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If step 2 errors with *"running scripts is disabled"*, run this once and retry:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Then verify — this checks your RAM headroom and the Quran text library, and does **not** download the model:

```powershell
python s0_check.py
```

You want to see `ALL CHECKS PASSED`.

---

## Step 2 — Generate the recording plan

```powershell
python s1_manifest.py
```

Writes `manifest.csv` — 150 rows, each one clip: which āyah, what to do, and the ground-truth label. **Ground truth is free here** because you're inducing errors on purpose: you know what's wrong before the model sees it. No expert annotator needed for this stage.

The plan is 10 short āyāt × 15 takes:

- **50 correct recitations** (5 per āyah)
- **100 deliberate single-error recitations** (10 per āyah)

> **Why 50 correct clips matter more than the errors.** They measure your **false-positive rate** — how often the model accuses a correct recitation of being wrong. Per the architecture doc, that's the metric that decides whether this product is trustworthy. A spike with only error clips can't compute precision at all, which is the mistake most people make here.

---

## Step 3 — Record (the real work: ~3–4 hours, split over days)

```powershell
python s2_record.py
```

It walks you through every row: prints the āyah, prints exactly what to do, records on Enter, lets you re-record, and saves to `clips/` with the ground truth in the filename. You can quit and resume anytime — it skips clips already recorded.

### Recording conditions — keep these constant

| | |
|---|---|
| Room | Quiet, no fan/AC, door closed. Soft furnishings help. |
| Mic | Your laptop mic is **fine**. Do not switch mics partway through. |
| Distance | ~25 cm, slightly off-axis so you don't pop the mic on ب and ق. |
| Level | Normal recitation voice. Don't lean in for the error takes. |
| Pace | **Murattal** — slow and measured. Not fast (*ḥadr*), not melodic (*mujawwad*). |
| Waqf | Stop cleanly at the end of the āyah. This matters — qalqalah and *madd ʿāriḍ* only appear when you stop. |

### The three rules that make or break this data

1. **One error per clip.** If the instruction says shorten the madd, everything else must be correct. Two errors in one clip makes the result unattributable.
2. **Don't perform the error.** Make it the way a real learner would — a natural slip, not a cartoon. If you exaggerate, you'll measure the model on errors your users will never make and get a falsely optimistic number.
3. **Vary the correct takes.** Across your 5 `OK` clips per āyah, vary volume, speed, and starting pitch a little. Identical takes overstate how stable the model is.

**Recruit 2–3 other Uzbek or Russian speakers if you can** — ideally one who recites well and one beginner. Have them do the 50 correct clips at minimum. Single-speaker results won't generalize, and your own voice is the one voice the eventual product does *not* need to work on. Put their clips in `clips_<name>/` and pass `--clips-dir` to `s3`.

---

## Step 4 — Run the model

Close Chrome first. Then:

```powershell
python s3_transcribe.py
```

First run downloads the model (2.42 GB) to your HuggingFace cache. It prints timing after the first clip so you'll know immediately whether the speed estimate held. Results go to `results.json`.

If you see `MemoryError` or the process gets killed:

```powershell
python s3_transcribe.py --dtype bfloat16
```

---

## Step 5 — Get the number

```powershell
python s4_score.py
```

Prints the decision-gate table: false-positive rate on correct clips, and detection recall broken down by error type. Also writes `scored.csv` so you can inspect individual clips.

---

## Step 6 — typed errors (added after Step 0)

```powershell
python s5_typed_errors.py --demo    # see it work on the al-Kawthar case
python s5_typed_errors.py           # annotate results.json -> typed.csv
```

Step 0 showed the Spaces report everything as *ḥarf nāqiṣ / ḥarf zāʾid* — raw
insert/delete. `s5` is the Layer 4 prototype that fixes this: it run-length
decodes the phoneme string before diffing, so `نننن → نن` reads as
**GHUNNA_SHORT (2 counts, expected 4)** instead of "two missing letters".

`s4` answers *did it detect anything?* `s5` answers **did it name the right
mistake?** — which is the number that actually decides whether you can build
pedagogy on this.

## The decision gate

Read these off `s4_score.py`:

| Outcome | Meaning | Do this |
|---|---|---|
| **FP rate < 20%** and **recall > 50%** on substitution + qalqalah + ghonna | Architecture holds | Proceed to full system design. Scope v1 to the error types that scored well and ship only those. |
| **FP rate 20–40%** | Usable but not trustworthy yet | Add a confidence layer using `phonemes.probs`; only surface errors above a probability threshold. Re-score. |
| **FP rate > 40%** | Model is hallucinating errors on correct recitation | Do **not** build error-reporting UI on this. Go to the fallback in the architecture doc: 8–12 binary classifiers on frozen embeddings. |
| **Recall < 30% across the board** | Expert-data bias (Risk 1) confirmed | The model is snapping learner audio onto correct phonemes. You need your own learner data before this works. Fallback applies. |

Expect **duration/madd errors to score differently from substitutions** — they're a genuinely different signal (timing vs. identity). Read those rows separately; it's normal for one to work well while the other doesn't, and that alone would shape your v1 scope.

---

## What I could and couldn't verify

Verified live on your machine: `quran-transcript` installs on Python 3.13; the `Aya` / `quran_phonetizer` / `MoshafAttributes` API works as scripted; all 10 āyāt produce the phonemes and ṣifāt the plan targets; `MoshafAttributes` needs exactly 5 required fields; madd length changes the phoneme string as the scoring relies on.

**Not verified:** anything that requires downloading the 2.42 GB model — so `s3_transcribe.py`'s call into `quran_muaalem` is written from the published API and two working HuggingFace Spaces, not from a local run. If it breaks, it'll break on the first clip with a clear error. Paste it to me and I'll fix it.

Also note the library genuinely misspells its own function as `expalin_sifat` — `s3` tries both spellings.
