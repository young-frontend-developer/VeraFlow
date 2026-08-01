# Tolerance calibration

**This is the gate before any learner sees the app.**

You record ayat you certify as **correct**. The harness runs them through the
real pipeline and reports every check that fired. Because the input is correct
by your certification, *every fire is a false positive* — no expert labelling
needed, no ambiguity about ground truth. That is what makes this cheap enough to
re-run after every change.

---

## The loop

```bash
cd api

# 1. list your recordings (see manifest.example.csv)
#    calibration/manifest.csv

# 2. run — transcribes and caches (slow the first time, ~1-3 s per clip)
py -3.13 tools/calibrate.py

# 3. read the "need" column, edit config/tolerances.json

# 4. re-run the identical command — scores from cache in about a second
py -3.13 tools/calibrate.py
```

Step 4 is the point of the design: **thresholds live in `config/tolerances.json`,
never in engine code**, and changing one does not re-run inference. Use
`--recompute` when the audio or the model changes, `--suggest` to have the
thresholds that would zero out this sample written to a separate file for review.

---

## manifest.csv

```csv
path,sura,aya,start_word,num_words,reciter,note
clips/103_001_take1.wav,103,1,,,rahmatulloh,slow murattal
clips/112_001_take1.wav,112,1,,,ustadh-ali,phone mic
clips/002_255_a.wav,2,255,0,6,ustadh-ali,first segment only
```

| column | meaning |
|---|---|
| `path` | relative to `calibration/`, or absolute |
| `sura`, `aya` | required |
| `start_word`, `num_words` | blank = the whole ayah. Must be a legal cut (see `engine/ranges.py`) |
| `reciter` | **fill this in** — the per-reciter breakdown is the most important table in the report |
| `note` | mic, tempo, room; whatever you will want to know later |

Recordings and the transcription cache are git-ignored. They are personal
recitations and they are yours.

---

## Reading the report

- **`clips fired` / `eligible`** — the false-positive rate for that check. `eligible`
  excludes clips where the check could not have fired at all (no madd letter, no
  ghunnah), so a `0/0` is *no evidence*, not a pass.
- **`margins`** — min / median / max, in QPS units (roughly one ḥarakah each).
  This is the number to set thresholds from.
- **`need`** — the `min_delta` that would silence every false positive **in this
  sample**. It is a bound from what you recorded, not a safe value.
- **`suppressed`** — fires that a threshold already swallowed. Watch this column
  after raising a threshold: it is where real errors will start disappearing too.
- **Ṣifa table** — observation only. `typed_diff` compares phoneme strings and
  never reads the predicted ṣifāt, so tafkheem / hams / shidda / jahr have **no
  detector**. Those rates are the false-positive floor for a detector that does
  not exist yet — evidence about whether it is worth building.

---

## Two honest limits

**Raising a threshold hides real errors of the same size.** A `min_delta` of 3 on
`MADD_SHORT` means a 4-count madd recited as 2 goes unmentioned. The report will
never tell you that trade is acceptable; only you can.

**One reciter is not a calibration.** Already on record for this project: an
attempt to certify a "correct" set with a single voice produced ص reading as س on
4 of 4 takes — the reciter could not certify their own recitation. The report
prints a per-reciter table and shouts when there is only one. Get a second voice
before trusting any number here.
