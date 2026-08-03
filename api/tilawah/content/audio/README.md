# Isolated letter recordings

One short file per confusable letter PAIR — the sound a learner has to be able
to tell apart. `sad_zay.mp3` is «ص» then «ز», slowly, nothing else: no ayah, no
words, no voice-over. The drill in a coaching card is about one sound, and
playing a whole ayah to teach it is what this replaces.

## Naming

The filename is the `audio_pair` value in the registry, minus the `audio/`
prefix. `"audio_pair": "audio/sad_zay.mp3"` is served from `sad_zay.mp3` here.

## Why an empty directory is checked in

`coaching.audio_url()` tests for the FILE, not for the registry field, and the
client renders the practice button only when a URL comes back. So every one of
these buttons is currently hidden — which is correct, and which is why there is
no dead control on any card. Drop a file in and its button appears with no code
change.

`coaching.missing_audio()` lists every entry still waiting for one; it is
surfaced through `/api/meta` so the gap stays visible.

## Still needed

All 13 entries that name a recording. Run:

    py -3.13 -c "from tilawah.content import coaching; print(*coaching.missing_audio(), sep='\n')"
