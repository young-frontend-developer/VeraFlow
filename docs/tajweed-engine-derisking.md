# Tilawah — De-risking the Tajweed Feedback Engine

**Status:** pre-implementation technical assessment
**Date:** 2026-07-30

---

## 1. The core reframe

Tajweed feedback is **not** a speech-to-text problem, and treating it as one is the most common way these projects fail.

In general L2 pronunciation assessment (English learners, etc.) you don't know what the speaker intended to say, so you must jointly infer content and quality. That's genuinely hard and error-prone.

Quran recitation gives you an enormous asymmetry:

> **The correct answer is fully computable in advance.** The learner selects an ayah. Given the Uthmani text plus a riwayah (Ḥafṣ ʿan ʿĀṣim for your target market), the complete expected phoneme sequence — *including* madd lengths in ḥarakah counts, ghunnah placement and duration, idghām/ikhfāʾ realization, qalqalah — is **deterministic**. It follows from rules, not from statistics.

So the task is not "what did they say?" It's:

**"Here is exactly what should have been produced. Measure the delta."**

That turns an open-ended ML problem into a constrained alignment-and-diff problem. Everything below follows from this.

---

## 2. What already exists (this is the big finding)

A project called **Muaalem / المعلم القرآني** (Abdullah, `obadx`) published in late 2025 and presented at ICML 2026 has open-sourced most of the foundation layer:

| Asset | What it is | Where |
|---|---|---|
| **Muaalem dataset** | ~890 hours, 300K+ annotated utterances of expert recitation | [`obadx/mualem-recitations-annotated`](https://huggingface.co/datasets/obadx/mualem-recitations-annotated) |
| **QPS (Quran Phonetic Script)** | Two-level annotation scheme: phoneme level (letters + short/long vowels) **and ṣifa level** (articulation attributes per phoneme). Purpose-built for Tajweed — IPA cannot express this. | in `quran-transcript` |
| **Multi-level CTC model** | `Wav2Vec2BertForMultilevelCTC`, ~0.6B params. Predicts phonemes *and* their ṣifāt jointly. **MIT licensed.** ~6.6K downloads. | [`obadx/muaalem-model-v3_2`](https://huggingface.co/obadx/muaalem-model-v3_2) |
| Streaming variant | RNN model for live/incremental feedback | [`obadx/muaalem-streaming-rnn-v0`](https://huggingface.co/obadx/muaalem-streaming-rnn-v0) |
| Small + TorchScript variants | `muaalem-model-v3-mini`, `muaalem-v3_2-torchscript` — a path to on-device later | HF, same org |
| **Waqf segmenter** | wav2vec2-BERT fine-tune that splits recitation at pause points | [`obadx/recitation-segmenter-v2`](https://huggingface.co/obadx/recitation-segmenter-v2) |
| Text → expected-phoneme library | Generates the QPS target sequence from Quranic text | [`quran-transcript`](https://github.com/obadx/quran-transcript) |
| Reported result | **0.16% average Phoneme Error Rate** on their test set | [arXiv:2509.00094](https://arxiv.org/abs/2509.00094) |

**This is roughly two years of work handed to you under a permissive license.** Do not rebuild it. Your engineering effort belongs in layers 4, 5, and 6 below — and in the data asset in §5.

⚠️ **Verify licensing yourself before commercial launch.** The model card says MIT and the paper says open-source/CC0, but the *underlying reciters' audio* is a separate rights question from the annotations. Get this checked before you monetize.

---

## 3. Reference architecture

```
[0] CAPTURE          16kHz mono, per-ayah push-to-record, VAD trim
                      ↓
[1] SEGMENT          recitation-segmenter-v2 → split at waqf points
                      ↓
[2] EXPECTED  ←────── ayah id + riwayah → quran-transcript → target QPS
    (deterministic,   (phonemes + ṣifāt + madd counts) — computed, not predicted
     cacheable)
                      ↓
[3] RECOGNIZE        muaalem multi-level CTC → hypothesis QPS
                      (phoneme seq + per-phoneme ṣifāt + CTC frame timings)
                      ↓
[4] DIFF             articulatory-weighted alignment: expected vs hypothesis
                      → TYPED errors, not a score
                      ↓
[5] EXPLAIN          typed error → scholar-authored rule content (uz/ru)
                      + expert audio snippet of that phoneme in that position
                      + targeted drill
                      ↓
[6] PERSIST          error events → learner error profile → drives lesson
                      recommendation AND Hifz scheduling
```

### Layer 4 — partly already built (revised)

Two things found while specifying the spike:

- **The model takes the expected phonetization as an _input_**, not just the audio: `muaalem([wave], [phonetizer_out], sampling_rate=16000)`. It is designed for compare-against-known-target, which independently validates §1.
- `pip install quran-muaalem` ships `explain_for_terminal()` and `quran_muaalem.explain.expalin_sifat` (yes, misspelled in the library) — reference-vs-heard ṣifāt alignment already exists.

So layer 4 is less greenfield than assumed. Your work is refining it — the weighted cost function below, the error taxonomy, and the pedagogical ranking — not building alignment from zero.

Also: **madd duration is visible in the phoneme string itself.** `quran_phonetizer` encodes a 4-count madd as `اااا` and a 2-count as `اا`; ghunnah as `نننن`; qalqalah as a `ڇ` marker. Verified locally. Duration errors are therefore measurable as a plain string diff — no separate timing model needed for a first version.

Do **not** use plain Levenshtein distance. Substitution cost must encode articulatory distance so the diff is pedagogically meaningful:

- ص → س is a **near miss** → report as a *tafkhīm* (emphasis) error, one specific correction.
- ص → ك is a **gross error** → different message entirely.

Emit **typed errors**, never a single "87% score":

| Error type | Signal used | Example |
|---|---|---|
| Makhraj substitution | phoneme mismatch | ع read as ء |
| Ṣifa mismatch | right letter, wrong attribute | ط read without iṭbāq |
| Duration error | CTC frame timings → ḥarakah counts | madd munfaṣil held 2 counts instead of 4 |
| Ghunnah error | ṣifa level + duration | nūn mushaddadah with no nasalization |
| Qalqalah error | ṣifa level | missing bounce on qāf |
| Insertion / deletion | alignment gaps | skipped or added word |

A typed error is directly actionable — it maps to one rule, one drill, one audio example. A percentage score teaches nothing.

### Layer 5: where LLMs belong — and where they must not go

**Never let an LLM decide or state a Tajweed ruling.** The rule name, the correction, and the reason come from deterministic templates over scholar-authored content. The LLM's *only* jobs are:

1. Phrasing that content warmly and at the right level in Uzbek/Russian.
2. Triage — which one or two of six detected errors to mention first.
3. Encouragement framing.

A hallucinated ruling about the Quran is an unrecoverable trust failure. Architect so it is structurally impossible, not merely unlikely.

---

## 4. Honest risks, ranked

### Risk 1 — Train/test mismatch: the model learned from experts, your users are learners 🔴

**This is the one that can sink the product, and it is currently unmeasured.**

The 890h Muaalem corpus is expert reciters. The 0.16% PER is on in-distribution expert audio. A phoneme recognizer trained only on *correct* recitation develops a strong prior toward correct output — it snaps learner attempts onto the nearest valid phoneme, which silently erases the exact error you're trying to surface. This is the well-known failure mode in mispronunciation detection (why GOP / Goodness-of-Pronunciation confidence scoring exists as a separate layer).

The project's own out-of-distribution set — [`ood_muaalem_test`](https://huggingface.co/datasets/obadx/ood_muaalem_test), sourced from Tarteel logs and `iqraa_eval` — is **219 clips**, and its benchmark-results repo is **empty**. Learner-facing accuracy is effectively unpublished.

**→ You must measure this yourself before committing your architecture. See §6.**

### Risk 2 — False positives are worse than false negatives here 🔴

Telling a sincere Muslim they mispronounced the Quran when they did not is not a normal UX bug. It is religiously and emotionally costly and it destroys trust permanently.

Design consequences, not optional:
- Tune to a **high-precision** operating point; accept lower recall.
- Ship a confidence tier: confident errors → direct correction; uncertain → *"this one I'm not sure about — worth checking with your teacher."*
- Never a bare "wrong." Always rule + reason + how to fix + example.
- This also reinforces your positioning: a companion between lessons, not a judge.

### Risk 3 — Style, dialect, and voice variance 🟡

Murattal vs. mujawwad vs. ḥadr tempo; different maqāmāt; children's voices (very different formants, badly underrepresented in most corpora); riwayah/madhhab differences in madd counts. Each degrades accuracy if unhandled. Constrain aggressively in v1: one riwayah (Ḥafṣ), murattal tempo, adult voices first.

### Risk 4 — L1 interference — and your unfair advantage 🟢

Uzbek and Russian speakers have *specific, predictable* substitution patterns: ع/ء collapse, ح → х, ط → т, ق → к, ص → с, و → в, and general loss of emphatics. Nobody has built an L1-conditioned error prior for these languages.

This is a genuine, defensible differentiator and it is cheap: it's a prior over your error taxonomy plus targeted drill content. It raises precision (expected errors are more likely) and makes feedback feel uncannily personal. **Prioritize it — it's the highest ratio of differentiation to effort in the whole product.**

### Risk 5 — Cost and latency 🟢 (good news)

CTC is a **single forward pass** — no autoregressive decoding, so none of the per-token cost dynamics of LLM inference. A 0.6B wav2vec2-BERT on a modest GPU (L4/A10) processes audio at many multiples of realtime when batched. Per-recitation cost lands in **fractions of a cent**, and p95 latency for a 10-second ayah is achievable well under a second end-to-end.

Your cost model is dominated by GPU *idle* time, not inference. Implications: batch aggressively, scale to zero off-peak, and know that the `-mini` + TorchScript variants give you a credible on-device path later — which would cut inference cost to zero and work offline, a real advantage in your markets.

---

## 5. The data strategy *is* the moat

The model is MIT-licensed and available to every competitor. What isn't:

**Learner recordings from Uzbek/Russian speakers, with expert-annotated errors.**

Build the collection loop into v1 from day one:
1. Every recitation attempt is stored (with explicit, clearly-worded consent — this is religiously sensitive personal data; be scrupulous and let users delete it).
2. User can flag "I think this feedback was wrong" — free, high-signal hard negatives.
3. A small paid panel of qualified teachers labels a queue, prioritized by model uncertainty (active learning).
4. Fine-tune on your own learner distribution. Compounding advantage.

**Also grab [QDAT](https://huggingface.co/datasets/obadx/qdat)** (~1,500 clips of correct *and incorrect* recitation across 3 Tajweed rules). It's narrow, but it's one of the few public sources of labeled *errors* rather than correct recitation — invaluable as an initial evaluation set.

---

## 6. The decision gate: a 2-week spike

Do not design the rest of the system until you have this number.

| Days | Task | Output |
|---|---|---|
| 1–3 | Run `muaalem-model-v3_2` locally on expert audio. Confirm QPS output parses; understand the ṣifa schema. | Working inference script |
| 4–6 | Build expected-QPS generation with `quran-transcript` for ~10 ayat. Build the weighted diff. | End-to-end pipeline on correct audio → should report zero errors |
| 7–10 | Collect 150–200 clips: you + 3–5 Uzbek/Russian speakers, 3 proficiency levels, with **deliberately induced known errors** (read ص as س; shorten a madd to 2 counts; drop a ghunnah; skip a word). You know ground truth by construction — no expert labeling needed yet. | Labeled eval set |
| 11–14 | Measure **precision and recall per error type**. | The number |

**Gates:**

- **Precision > 80%, recall > 50% on gross errors** → the architecture holds. Proceed to full system design; scope v1 around the error types that scored well.
- **Precision 60–80%** → add a GOP/confidence layer and ship only high-confidence error types. Still a product.
- **Precision < 60%** → the expert-data bias in Risk 1 is real. **Pivot to the fallback below before building any user-facing "you made a mistake" UI.**

### Fallback architecture (keep in your pocket)

If open-vocabulary error detection proves too noisy on learners, narrow radically: instead of "detect any Tajweed error," train **8–12 dedicated binary classifiers** on top of the frozen wav2vec2 embeddings, one per high-frequency Uzbek/Russian-L1 error. Far more tractable, far easier to hit high precision, needs much less labeled data —

— and pedagogically **better**. A learner given three specific, correct, fixable errors improves. A learner handed a firehose of forty flagged phonemes quits. The fallback may well be the right v1 regardless of what the spike says.

---

## 7. What this means for the other three pillars

Once layer 6 exists — a persistent, typed **learner error profile** — the rest of the product falls out of it almost for free, and stops being three separate apps:

- **Lessons** → recommended by which rules the learner actually fails, not a fixed syllabus.
- **Exercises** → generated as drills targeting their specific open error types.
- **Hifz planning** → review scheduling weighted by *both* forgetting curve *and* Tajweed error density on each passage. A memorized ayah recited with a makhraj error is not "done." No competitor models this.

That shared error profile is the architectural spine of the whole platform. Design it deliberately in the next phase, not as an afterthought of the audio pipeline.

---

## 8. The tolerance gate (added 2026-08-01, Phase 2)

§4 risk 2 says false positives are the expensive failure here. It did not say how
you would ever know you had one. This section closes that.

**The gate:** before any learner sees the app, a set of recitations *certified
correct* must pass through the full pipeline and be measured. Every check that
fires on one of them is a false positive by construction — no expert labelling,
no annotation queue, no ambiguity about ground truth. That is what makes this
runnable after every change rather than once before launch.

Built as `api/tools/calibrate.py`; see `api/calibration/README.md` for the loop.

### Why a tolerance layer had to exist at all

Two takes of the same ayah by the same reciter, both correct, do not produce the
same phoneme string. A madd held four counts in one take reads as five in the
other, and the diff dutifully reports `MADD_LONG` on correct recitation. So every
gradient check — madd length, ghunnah length, shadda length — needs a threshold
below which a deviation is measured and *not shown*.

Those thresholds are empirical facts about a microphone, a model and a reciter,
not decisions about the code. They live in `api/config/tolerances.json` and
nowhere else, and changing one does not require a deploy or re-running inference.

### What the harness deliberately refuses to do

- **It ships no guessed thresholds.** Every `min_delta` is 1, which reproduces the
  pre-tolerance behaviour exactly. Inventing a number before measuring is how a
  calibration tool becomes a way of hiding errors.
- **It never auto-applies its own suggestions.** `--suggest` writes a separate
  file for review. Auto-applying would fit thresholds to whatever was recorded
  last.
- **It does not pretend a threshold can fix a wrong letter.** Discrete checks
  (`SUB_SAD_SEEN`, `DELETION`) report no margin, because there is no gradient to
  threshold. If those fire on correct audio, the answer is a narrower scope or a
  better model — not a tuning knob.
- **It counts a false rejection as equal harm.** A correct recitation thrown out
  by the quality gate or the collapse detector never reaches a check, so it would
  score as a silent pass. Those are listed separately and labelled.

### The limit that no amount of tooling removes

A zero false-positive rate over eight clips from one reciter is eight clips from
one reciter. The report prints a per-reciter table and refuses to be quiet about
a single-voice sample — which is the already-recorded ground-truth problem for
this project: an attempt to certify a "correct" set with one voice produced ص
reading as س on 4 of 4 takes. **A second qualified reciter is a prerequisite for
this gate to mean anything**, and that is a recruiting task, not an engineering
one.

### Ṣifa checks: measured, not built

`typed_diff` compares phoneme strings and never reads the ṣifāt the model also
predicts, so `TAFKHEEM_ADDED`, `HAMS_LOST`, `SHIDDA_LOST` and `JAHR_LOST` have
**no detector** despite having registry entries. The harness reports
reference-vs-predicted ṣifa disagreement anyway, as observation only: that
disagreement rate on correct audio is the false-positive *floor* for any ṣifa
detector built on this model. If it is high, the detector is not buildable at
this operating point, and that is worth learning from a config file rather than
from a learner.

---

## 9. Registry v3 — a sourced content base (2026-08-01)

The registry is no longer a developer's paraphrase. `tajweed_error_registry_v3.json`
is generated by `api/tools/apply_v3_patch.py` from the v2 base plus a patch
grounded in **«Тажвид қоидалари»** (Ziyovuddin Rahim, Odilxon qori Yunusxon
o'g'li; Tashkent Islamic University, 2011; ISBN 978-9943-390-26-3; reviewed by
Abdulaziz Mansur; approved under Committee on Religious Affairs recommendation
1204 of 17 June 2011). Every entry carries a `source_ref` to the lesson it
derives from.

- 34 → **40 entries**. 6 added, 4 rewritten, 122 terminology corrections across
  29 entries — heavy letters are *yo'g'on*, not *qalin*; the technical pair is
  *iste'lo/istifola*, not *mufaxxam/moraqaq*.
- **Everything stays `status: "draft"`.** The merge does not touch
  `content/rules.json`, so nothing new reaches a learner. Promotion still
  requires a qori.
- `tajweed_error_registry_v2.json` stays in the repo as the auditable "before",
  and `docs/registry-v3-merge-report.md` records exactly what changed. **Do not
  hand-edit v3** — edit the patch and re-run the script.

### The qalqala shadda exception (2-dars) — already correct, now pinned

A qalqala letter carrying shadda mid-word, joined to what follows, takes **no**
qalqala; qalqala applies at lozim sukun and oriz sukun only. Without that
exclusion `QALQALAH_MISSING` would false-fire on every joined shadda in the
Quran.

Measured rather than assumed: `quran_transcript` **already applies it**, and
distinguishes the *same letter* by position —

| position | QPS | `qalqla` |
|---|---|---|
| `تَبَّتْ` — ب shadda mid-word, joined | `تَببَ` | `not_moqalqal` |
| `وَتَبَّ` — same ب, final at waqf | `ببڇ` | `moqalqal` |

So the rule is **not reimplemented here** — restating a rule the phonetizer
already applies is how the two silently drift apart. It is pinned by tests
instead, which fail loudly if that upstream guarantee ever changes. The one
place our own code duplicated the logic (`JAHR_LOST` excluded qalqalah letters
by letter identity) now tests the ṣifa, so it inherits the exception rather
than restating it.

### The ف/و edge (6-dars) — computed, deliberately inert

`MIM_IZHAR_SHAFAWIYA_WRONG` is weighted 1.5× when the letter after a sukunli
miym is ف or و, because their makhraj sits close enough to miym that an
unintended ixfo slips in. **Nothing consumes this yet, on purpose:** all three
`MIM_*` entries are `detection_confidence: "low"`, their `ahkam` group is
excluded from `in_scope()`, and weighting a detector that does not run would be
theatre. `detection_weight()` computes it and a test pins it, so promoting the
entry is a one-line change rather than a re-derivation.

---

## Sources

- [arXiv:2509.00094 — Automatic Pronunciation Error Detection and Correction of the Holy Quran's Learners Using Deep Learning](https://arxiv.org/abs/2509.00094) (ICML 2026)
- [Muaalem project page](https://obadx.github.io/prepare-quran-dataset/) · [prepare-quran-dataset](https://github.com/obadx/prepare-quran-dataset) · [quran-transcript](https://github.com/obadx/quran-transcript) · [recitations-segmenter](https://github.com/obadx/recitations-segmenter)
- [`obadx/muaalem-model-v3_2`](https://huggingface.co/obadx/muaalem-model-v3_2) · [`obadx/recitation-segmenter-v2`](https://huggingface.co/obadx/recitation-segmenter-v2) · [`obadx/qdat`](https://huggingface.co/datasets/obadx/qdat) · [`obadx/ood_muaalem_test`](https://huggingface.co/datasets/obadx/ood_muaalem_test)
- [arXiv:2305.06429 — Mispronunciation Detection of Basic Quranic Recitation Rules using Deep Learning](https://arxiv.org/abs/2305.06429)
- [The Tarteel Dataset: Crowd-Sourced and Labeled Quranic Recitation](https://openreview.net/forum?id=TAdzPkgnnV8) · [`tarteel-ai/everyayah`](https://huggingface.co/datasets/tarteel-ai/everyayah)
- [QDAT: A data set for Reciting the Quran](https://www.researchgate.net/publication/350823149_QDAT_A_data_set_for_Reciting_the_Quran)
