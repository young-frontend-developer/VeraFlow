# -*- coding: utf-8 -*-
"""
s0_check.py - verify the environment BEFORE downloading the 2.42 GB model.

Run:  python s0_check.py
Want: "ALL CHECKS PASSED"
"""
import sys
import shutil

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ok = True


def check(label, fn):
    """Run one check, print PASS/FAIL, never crash the whole script."""
    global ok
    try:
        detail = fn()
        print(f"  [PASS] {label}" + (f" - {detail}" if detail else ""))
    except Exception as e:
        ok = False
        print(f"  [FAIL] {label}\n         {type(e).__name__}: {e}")


print("=" * 68)
print("Tilawah spike - environment check")
print("=" * 68)

# ---------------------------------------------------------------- python
print("\nPython")


def _py():
    v = sys.version_info
    if v[:2] == (3, 14):
        raise RuntimeError(
            "You are on Python 3.14. torch/numba wheels are unreliable here.\n"
            "         Recreate the venv with:  py -3.13 -m venv .venv"
        )
    if v < (3, 10):
        raise RuntimeError(f"Python {v.major}.{v.minor} too old; quran-muaalem needs >=3.10")
    return f"{v.major}.{v.minor}.{v.micro}"


check("version is 3.10-3.13", _py)


def _venv():
    if sys.prefix == sys.base_prefix:
        raise RuntimeError("Not inside a venv. Run:  .\\.venv\\Scripts\\Activate.ps1")
    return sys.prefix


check("running inside the venv", _venv)

# ---------------------------------------------------------------- packages
print("\nPackages")
check("numpy", lambda: __import__("numpy").__version__)
check("soundfile", lambda: __import__("soundfile").__version__)
check("sounddevice", lambda: __import__("sounddevice").__version__)
check("quran_transcript", lambda: __import__("quran_transcript").__name__)
check("torch", lambda: f"{__import__('torch').__version__} (CPU build is expected)")
check("quran_muaalem", lambda: __import__("quran_muaalem").__name__)

# ---------------------------------------------------------------- resources
print("\nSystem resources")


def _ram():
    # Windows-only, no extra dependency: ask the OS via ctypes.
    import ctypes

    class MS(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    st = MS()
    st.dwLength = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
    avail = st.ullAvailPhys / (1024 ** 3)
    total = st.ullTotalPhys / (1024 ** 3)
    msg = f"{avail:.1f} GB free of {total:.1f} GB"
    if avail < 3.5:
        msg += "  <-- TIGHT. Close Chrome before running s3_transcribe.py"
    return msg


check("RAM headroom", _ram)


def _disk():
    free = shutil.disk_usage(".").free / (1024 ** 3)
    if free < 6:
        raise RuntimeError(f"only {free:.1f} GB free; model needs ~2.5 GB plus cache")
    return f"{free:.0f} GB free"


check("disk space", _disk)


def _mic():
    import sounddevice as sd

    ins = [d for d in sd.query_devices() if d["max_input_channels"] > 0]
    if not ins:
        raise RuntimeError("no input device found - is a microphone enabled?")
    return f"{len(ins)} input device(s), default: {sd.query_devices(kind='input')['name']}"


check("microphone", _mic)

# ---------------------------------------------------------------- pipeline
print("\nQuran text pipeline (the part that must be exactly right)")


def _phon():
    from quran_transcript import Aya, MoshafAttributes, quran_phonetizer

    moshaf = MoshafAttributes(
        rewaya="hafs",
        madd_monfasel_len=4,
        madd_mottasel_len=4,
        madd_mottasel_waqf=4,
        madd_aared_len=4,
    )
    uth = Aya(103, 1).get().uthmani
    out = quran_phonetizer(uth, moshaf, remove_spaces=True)
    if out.phonemes != "وَلعَصر":
        raise RuntimeError(f"unexpected phonemes for 103:1 -> {out.phonemes!r}")
    sad = [s for s in out.sifat if s.phonemes.strip() == "ص"]
    if not sad or sad[0].tafkheem_or_taqeeq != "mofakham":
        raise RuntimeError("sad in 103:1 is not marked mofakham - sifat schema changed")
    return f"103:1 -> {out.phonemes}  (sad = mofakham/motbaq, as expected)"


check("phonetizer + sifat", _phon)


def _madd():
    """The scoring in s4 relies on madd length being visible in the phoneme string."""
    from quran_transcript import Aya, MoshafAttributes, quran_phonetizer

    uth = Aya(109, 1).get().uthmani
    mk = lambda n: MoshafAttributes(
        rewaya="hafs", madd_monfasel_len=n, madd_mottasel_len=4,
        madd_mottasel_waqf=4, madd_aared_len=n,
    )
    p4 = quran_phonetizer(uth, mk(4), remove_spaces=True).phonemes
    p2 = quran_phonetizer(uth, mk(2), remove_spaces=True).phonemes
    if p4 == p2 or len(p4) <= len(p2):
        raise RuntimeError("madd length is not changing the phoneme string")
    return f"4-count is {len(p4) - len(p2)} chars longer than 2-count"


check("madd length affects phonemes", _madd)

print("\n" + "=" * 68)
print("ALL CHECKS PASSED - run  python s1_manifest.py" if ok
      else "SOME CHECKS FAILED - fix the [FAIL] lines above first")
print("=" * 68)
sys.exit(0 if ok else 1)
