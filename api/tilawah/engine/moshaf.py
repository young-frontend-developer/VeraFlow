# -*- coding: utf-8 -*-
"""Single source of truth for recitation settings.

The spike learned this the hard way: if s1 and s3 disagree on MoshafAttributes,
every clip looks wrong for reasons that have nothing to do with the learner.
Import MOSHAF from here everywhere. Never construct MoshafAttributes inline.
"""
from quran_transcript import MoshafAttributes

RIWAYAH = "hafs"        # Hafs 'an 'Asim - the uz/ru market. MVP supports only this.

MOSHAF = MoshafAttributes(
    rewaya=RIWAYAH,
    madd_monfasel_len=4,
    madd_mottasel_len=4,
    madd_mottasel_waqf=4,
    madd_aared_len=4,
)
