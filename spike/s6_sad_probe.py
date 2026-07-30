# -*- coding: utf-8 -*-
"""
s6_sad_probe.py - is the model wrong about your ص, or are you not producing it?

The phoneme head says س where the reference says ص. That alone cannot tell you
whose fault it is, so this probe asks the same question through two channels
that fail independently:

  CHANNEL A - the model's SIFA head.
      ص and س are a minimal pair. They agree on hams, rakhawa and safeer, and
      differ on exactly two features:

          ص  itbaq=motbaq    tafkheem=mofakham     (emphatic, pharyngealized)
          س  itbaq=monfateh  tafkheem=moraqaq      (plain)

      The sifa head is a different output head than the phoneme head, so it is
      a second opinion - but it is still the same model on the same audio, and
      a shared upstream encoder means it can be wrong the same way.

  CHANNEL B - direct acoustics, no model at all.
      Pharyngealization lowers the spectral centre of gravity of the sibilant
      frication. Plain /s/ concentrates energy high (~6-8 kHz); emphatic /sˤ/
      pulls it down (~4-5 kHz). Measured straight off the waveform, so it
      cannot inherit the model's bias.

The decisive comparison is WITHIN your own voice: your "correct" ص against your
deliberate SUB_SAD_SEEN س, same microphone, same session. If those two are
acoustically indistinguishable, you are producing one sound and calling it two.
The experts are an external anchor, but they are a different mic and room, so
absolute numbers across speakers are only suggestive.

Run:  python s6_sad_probe.py
      python s6_sad_probe.py --results results.json --clips-dir clips
"""
import argparse
import json
import sys

import numpy as np
import soundfile as sf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SR = 16000
SAD, SEEN = "ص", "س"          # ص  س

# Sibilant frication lives well above voicing; ignore everything below.
BAND_LO, BAND_HI = 1000.0, 7900.0
HF_EDGE = 6000.0                        # "plain /s/" energy sits above this

# A frame is only accepted as frication if the high band dominates the low band
# AND the waveform is noisy rather than periodic. Without both tests the search
# happily returns a vowel, reports a confident centroid, and means nothing.
MIN_SIB_RATIO = 2.0                     # energy(>4k) / energy(<1k)
MIN_ZCR = 0.35                          # /s/ runs 0.5-0.7; vowels below 0.3


def sibilant_units(sifat):
    """Sifa entries whose phoneme group contains ص or س."""
    out = []
    for i, s in enumerate(sifat or []):
        g = s.get("phonemes") or ""
        if SAD in g or SEEN in g:
            out.append((i, s))
    return out


def frame_energies(wave, n=400, hop=160):
    """25 ms frames, 10 ms hop -> (spectra, freqs, windowed frames)."""
    if len(wave) < n:
        wave = np.pad(wave, (0, n - len(wave)))
    idx = np.arange(0, len(wave) - n + 1, hop)
    frames = np.stack([wave[i:i + n] for i in idx])
    spec = np.abs(np.fft.rfft(frames * np.hanning(n), axis=1)) ** 2
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    return spec, freqs, frames


def find_sibilant(wave):
    """Locate the frication burst, or admit that there isn't one.

    وَٱلْعَصْرِ has exactly one sibilant, so the best-scoring frame is it - but
    only if that frame actually looks like frication. Two tests, because either
    one alone is fooled: high-over-low band energy (a vowel fails this) and
    zero-crossing rate (periodic voicing fails this).

    Returns (mean spectrum, freqs, diagnostics) with spectrum None when no
    frame qualifies. Reporting a number for a clip with no detectable sibilant
    would be worse than reporting nothing.
    """
    spec, freqs, frames = frame_energies(wave)
    total = spec.sum(axis=1)
    lo_e = spec[:, freqs < 1000.0].sum(axis=1) + 1e-30
    hi_e = spec[:, freqs > 4000.0].sum(axis=1)
    sib = hi_e / lo_e
    zcr = (np.abs(np.diff(np.sign(frames), axis=1)) > 0).mean(axis=1)

    ok = (total > np.percentile(total, 50)) & (sib >= MIN_SIB_RATIO) & (zcr >= MIN_ZCR)
    if not ok.any():
        best = int(np.argmax(np.where(total > np.percentile(total, 50), sib, 0)))
        return None, freqs, {"sib": float(sib[best]), "zcr": float(zcr[best])}

    scored = np.where(ok, sib, 0.0)
    peak = int(scored.argmax())
    thr = scored[peak] * 0.5
    lo = hi = peak
    while lo > 0 and scored[lo - 1] >= thr:
        lo -= 1
    while hi < len(scored) - 1 and scored[hi + 1] >= thr:
        hi += 1
    diag = {"sib": float(sib[peak]), "zcr": float(zcr[peak]),
            "t": peak * 0.01, "n_frames": hi - lo + 1}
    return spec[lo:hi + 1].mean(axis=0), freqs, diag


def sibilant_acoustics(path):
    wave, sr = sf.read(path, dtype="float32", always_2d=False)
    if wave.ndim > 1:
        wave = wave.mean(axis=1)
    if sr != SR:
        return None

    s, freqs, diag = find_sibilant(wave)
    if s is None:
        return {"found": False, **diag}

    band = (freqs >= BAND_LO) & (freqs <= BAND_HI)
    p, f = s[band], freqs[band]
    return {
        "found": True,
        "centroid": float((p * f).sum() / (p.sum() + 1e-30)),
        "peak": float(f[int(p.argmax())]),
        "hf_frac": float(p[f > HF_EDGE].sum() / (p.sum() + 1e-30)),
        **diag,
    }


def group_of(r):
    if r["error_category"] == "control":
        return "EXPERT"
    if r["error_code"] == "SUB_SAD_SEEN":
        return "YOUR DELIBERATE س"
    if r["has_error"] == 0:
        return "YOUR CORRECT ص"
    return None


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results.json")
    ap.add_argument("--clips-dir", default="clips")
    args = ap.parse_args()

    with open(args.results, encoding="utf-8") as f:
        res = json.load(f)["results"]

    rows = []
    for r in res:
        g = group_of(r)
        if g is None:
            continue
        rows.append((g, r))
    order = ["EXPERT", "YOUR CORRECT ص", "YOUR DELIBERATE س"]
    rows.sort(key=lambda x: (order.index(x[0]), x[1]["clip_id"]))

    # ------------------------------------------------ channel A: model sifat
    print("=" * 78)
    print("  CHANNEL A - what the model's SIFA head says about the sibilant")
    print("=" * 78)
    print("  ص = motbaq + mofakham      س = monfateh + moraqaq\n")
    print(f"  {'clip':24s} {'group':6s} {'itbaq':>10s} {'p':>6s} {'tafkheem':>10s} {'p':>6s}")
    print("  " + "-" * 68)

    a_tally = {g: [] for g in order}
    last = None
    for g, r in rows:
        if g != last:
            print(f"\n  --- {g} ---")
            last = g
        units = sibilant_units(r["predicted_sifat"])
        if not units:
            print(f"  {r['clip_id']:24s} {'-':6s}   no sibilant unit in prediction")
            continue
        for _, u in units:
            pr = u.get("probs") or {}
            itb, taf = u.get("itbaq"), u.get("tafkheem_or_taqeeq")
            print(f"  {r['clip_id']:24s} {u.get('phonemes',''):6s} "
                  f"{str(itb):>10s} {pr.get('itbaq', float('nan')):6.3f} "
                  f"{str(taf):>10s} {pr.get('tafkheem_or_taqeeq', float('nan')):6.3f}")
            a_tally[g].append((itb, taf))

    # ------------------------------------------- channel B: direct acoustics
    print("\n" + "=" * 78)
    print("  CHANNEL B - direct acoustics of the frication (no model involved)")
    print("=" * 78)
    print("  Pharyngealized ص pulls the spectral centroid DOWN vs plain س.\n")
    print(f"  {'clip':24s} {'centroid':>9s} {'peak':>8s} {'>6kHz':>7s} {'sib':>7s} {'zcr':>5s}")
    print("  " + "-" * 68)

    b_tally = {g: [] for g in order}
    b_missing = {g: [] for g in order}
    last = None
    for g, r in rows:
        if g != last:
            print(f"\n  --- {g} ---")
            last = g
        ac = sibilant_acoustics(f"{args.clips_dir}/{r['clip_id']}.wav")
        if ac is None or not ac["found"]:
            d = ac or {}
            print(f"  {r['clip_id']:24s}   NO FRICATION FOUND "
                  f"(best sib={d.get('sib', 0):.2f} zcr={d.get('zcr', 0):.2f})"
                  f"  -> unusable")
            b_missing[g].append(r["clip_id"])
            continue
        print(f"  {r['clip_id']:24s} {ac['centroid']:8.0f}Hz {ac['peak']:7.0f}Hz "
              f"{100*ac['hf_frac']:6.1f}% {ac['sib']:7.1f} {ac['zcr']:5.2f}")
        b_tally[g].append(ac["centroid"])

    # ------------------------------------------------------------ conclusion
    print("\n" + "=" * 78)
    print("  READING")
    print("=" * 78)

    def emphatic(pairs):
        return sum(1 for i, t in pairs if i == "motbaq" or t == "mofakham")

    print("  CHANNEL A (model sifa head)")
    for g in order:
        if a_tally[g]:
            n = len(a_tally[g])
            print(f"    calls emphatic  {g:20s} {emphatic(a_tally[g])}/{n}")

    print("\n  CHANNEL B (direct acoustics)")
    for g in order:
        if b_tally[g]:
            print(f"    mean centroid   {g:20s} {mean(b_tally[g]):6.0f} Hz  "
                  f"(n={len(b_tally[g])})")
        if b_missing[g]:
            print(f"    no frication    {g:20s} {len(b_missing[g])} clip(s): "
                  f"{', '.join(b_missing[g])}")

    exp_c, ok_c, sub_c = (mean(b_tally[g]) for g in order)
    a_ok, a_exp = a_tally["YOUR CORRECT ص"], a_tally["EXPERT"]

    print("\n  " + "-" * 74)
    if a_ok and a_exp and emphatic(a_exp) == len(a_exp) and emphatic(a_ok) == 0:
        print("  Channel A is unanimous both ways: every expert reads as emphatic, none")
        print("  of yours does. The sifa head is a SEPARATE output head from the phoneme")
        print("  head, so this is a second opinion rather than a restatement - but both")
        print("  heads sit on one shared encoder, so they can still be wrong together.")
        print("  Strong evidence, not proof. Channel B is what would close it.")

    if not b_tally["YOUR DELIBERATE س"]:
        print("\n  >> INCONCLUSIVE, and the missing piece is your deliberate س.")
        print("     The within-speaker comparison - your ص against your own س, same")
        print("     mic, same session - is the only part of this test that controls")
        print("     for speaker and recording chain. Without it, all that is left is")
        print("     a cross-speaker centroid comparison, and sibilant centroids vary")
        print("     enormously with vocal tract, mic response and codec. Yours at")
        if ok_c is not None and exp_c is not None:
            print(f"     {ok_c:.0f} Hz vs experts at {exp_c:.0f} Hz does NOT separate cleanly:")
            print(f"     the expert range alone spans {min(b_tally['EXPERT']):.0f}-"
                  f"{max(b_tally['EXPERT']):.0f} Hz.")
        print("\n     TO CLOSE IT: re-record SUB_SAD_SEEN at the same quality as your")
        print("     current correct takes, then:")
        print("       python s3_transcribe.py && python s6_sad_probe.py")
        return

    sep = abs(ok_c - sub_c)
    print(f"\n  Your correct ص vs your deliberate س: {sep:.0f} Hz apart.")
    if sep < 250:
        print("\n  >> You are producing ONE sound, not two. Your 'correct' ص is")
        print("     acoustically indistinguishable from the س you made on purpose.")
        print("     The model is right and the label is wrong. That is a pronunciation")
        print("     gap, not a model defect - and it is what the product exists to")
        print("     catch, so the finding is good news for the architecture and bad")
        print("     news for using your own voice as ground truth.")
    elif ok_c < sub_c:
        print("\n  >> You ARE making a contrast - your ص is measurably lower/darker than")
        print("     your deliberate س. The model is collapsing a distinction that is")
        print("     present in the audio. That is a real model limitation on accented")
        print("     speech, and no amount of re-recording fixes it.")
    else:
        print("\n  >> Your 'correct' ص is HIGHER (more plain-/s/-like) than your")
        print("     deliberate error take - the contrast runs backwards. Check the")
        print("     clips are labelled the way you think before reading anything here.")


if __name__ == "__main__":
    main()
