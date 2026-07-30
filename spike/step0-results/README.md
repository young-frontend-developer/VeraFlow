# Step 0 — live Space sanity check

**Date:** 2026-07-30
**Model:** `obadx/muaalem-model-v3_2` via HuggingFace Space
**Speaker:** project owner, Uzbek-accented Arabic (single speaker, n=2 clips)

> **Audio files not yet in this folder.** These findings are the owner's written
> report of what the Space displayed; the two WAVs were not transferred. Drop them
> in here as `correct.wav` and `al-kawthar-errors.wav` to complete the record.

## Results as reported

| Clip | Outcome |
|---|---|
| Correct recitation | similarity **1.0**, zero mistakes reported |
| Al-Kawthar with induced errors | caught **ghunnah shortening**, **ع→ء**, **ط→ت**, **ث→س**, and an **extra ه** |

## Key observation

The Space reports every finding as **حرف ناقص** (missing letter) or **حرف زائد**
(extra letter) — raw insert/delete only. No typed errors, no articulatory
weighting. **Substitutions appear as delete+insert pairs.**

## What this establishes

1. **Risk 1 (expert-data bias) is not fatal.** The model detected real errors in
   Uzbek-accented learner audio rather than snapping them onto correct phonemes.
   This was the single biggest unknown.
2. **No false positive on the correct clip** (1.0, zero mistakes). One clip is not
   a rate, but it is the right direction on the metric that matters most.
3. **The untyped output is a presentation-layer gap, not a model gap.** That Space
   uses `diff_match_patch` on the phoneme string, which can only emit ±1 ops. The
   model itself also returns per-phoneme ṣifāt, which that Space largely discards.

## Caveats on how far to update

- n=2, one speaker, deliberately induced (possibly exaggerated) errors.
- A single correct clip cannot establish a false-positive *rate*.
- The 150-clip spike is still required for per-error-type recall and FP rate.
