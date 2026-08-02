# -*- coding: utf-8 -*-
"""The whole ayah is the practice range. Splitting is a choice, not a policy.

Segmentation used to decide this for the learner: 4513 of 6236 ayat — 72% of
the Quran — arrived pre-cut into ~12 s chunks because inference is slow on
2 vCPU. Three things were wrong with that. The model reads long ayat correctly
(the Gradio demo does it on the same weights). everyayah serves whole-ayah
files only, so a split range had no reciter audio to play against it. And the
30 s audio ceiling meant the whole ayah was not merely un-offered but actively
rejected on ~40% of the Quran.

These tests pin the new contract: `whole` always exists, at any length, and
`parts` is an offer.
"""
import pytest

from tilawah import content
from tilawah.api.routes import ayah_segments
from tilawah.engine.audio import MAX_DURATION_S
from tilawah.engine.ranges import estimate_seconds, is_legal_range, n_words

# The longest ayah in the Quran, its two nearest rivals, and short ones that
# were never split at all.
LONGEST = (2, 282)
CASES = [LONGEST, (24, 31), (4, 12), (2, 255), (112, 1), (108, 1), (1, 1)]


@pytest.mark.parametrize("sura,aya", CASES)
def test_whole_is_the_entire_ayah(sura, aya):
    out = ayah_segments(sura, aya)
    assert out.whole.start_word == 0
    assert out.whole.num_words == n_words(sura, aya)
    assert is_legal_range(sura, aya, out.whole.start_word, out.whole.num_words)


@pytest.mark.parametrize("sura,aya", CASES)
def test_whole_carries_real_text_and_a_duration(sura, aya):
    """A `whole` with an empty preview or a 0 s estimate would be worse than no
    whole at all — the learner would be choosing blind."""
    out = ayah_segments(sura, aya)
    assert out.whole.uthmani
    assert out.whole.text_segments
    assert out.whole.seconds > 0


def test_the_longest_ayah_in_the_quran_is_offered_whole():
    """2:282 is the case the old design could not express: ~194 s, 129 words,
    24 forced parts and no way to recite it in one take."""
    out = ayah_segments(*LONGEST)
    assert out.whole.num_words == 129
    assert out.whole.seconds > 180
    assert len(out.parts) == 24        # still available, now as a choice


def slow_seconds(sura: int, aya: int) -> float:
    segs = content.segments_of(sura, aya)
    return estimate_seconds(sum(s["n_phonemes"] for s in segs), gate=True)


def test_the_audio_ceiling_covers_almost_the_whole_quran():
    """The ceiling is a MEASURED memory limit, not a preference.

    wav2vec2-BERT relative-position attention allocates (47*seconds)^2 * 256
    bytes: 52 s ran fine at 1.5 GB, 129 s died with a 9.4 GB allocation on an
    8 GB box. So the whole-ayah default cannot be unconditional, and the honest
    statement of the contract is a coverage number rather than "always".

    If this drops, whole-ayah practice has quietly stopped being the default
    for a chunk of the Quran and somebody needs to know.
    """
    total = 0
    over = 0
    for key in content._segments_file()["segments"]:
        sura, aya = (int(x) for x in key.split(":"))
        total += 1
        if slow_seconds(sura, aya) > MAX_DURATION_S:
            over += 1
    covered = 100 * (total - over) / total
    assert covered >= 98.5, (
        f"only {covered:.1f}% of the Quran fits the {MAX_DURATION_S:.0f}s "
        f"ceiling ({over} ayat over)")


def test_the_upload_limit_clears_the_audio_ceiling():
    """16 kHz 16-bit mono PCM is 32 KB/s and the recorder downsamples to that,
    so this is arithmetic rather than a guess. The upload limit must not be the
    thing that rejects a recitation the engine would have accepted."""
    from tilawah.config import settings

    assert MAX_DURATION_S * 16000 * 2 < settings.max_upload_bytes


def test_the_longest_ayah_is_over_the_ceiling_and_has_parts():
    """The residual case, stated out loud rather than left implicit: 2:282
    cannot be assessed in one take on this engine, and the parts control is
    what makes it practisable at all."""
    assert slow_seconds(*LONGEST) > MAX_DURATION_S
    assert len(ayah_segments(*LONGEST).parts) > 1


@pytest.mark.parametrize("sura,aya", [(112, 1), (108, 1), (1, 1), (114, 1)])
def test_short_ayat_offer_no_parts(sura, aya):
    """A one-part list is a control that does nothing. Parts appear only where
    there is a real choice to make."""
    out = ayah_segments(sura, aya)
    assert out.parts == []


@pytest.mark.parametrize("sura,aya", [LONGEST, (24, 31), (2, 255), (1, 7)])
def test_parts_tile_the_ayah_exactly(sura, aya):
    """The optional parts still have to be a partition — offering a choice that
    silently drops words would be worse than not offering it."""
    out = ayah_segments(sura, aya)
    pos = 0
    for p in out.parts:
        assert p.start_word == pos, f"gap or overlap at word {pos}"
        assert is_legal_range(sura, aya, p.start_word, p.num_words)
        pos += p.num_words
    assert pos == out.whole.num_words


@pytest.mark.parametrize("sura,aya", CASES)
def test_nothing_is_split_without_being_asked(sura, aya):
    """The property the whole change is about: whatever the ayah, the range you
    get by default covers all of it."""
    out = ayah_segments(sura, aya)
    assert out.whole.num_words == n_words(sura, aya)
