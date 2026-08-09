// Microphone capture with a live level read.
//
// Ask for the raw signal: browser AGC and noise suppression are tuned for phone
// calls, and they reshape exactly the spectral detail the tajweed engine
// measures. The server's quality gate should judge the real room, not a
// processed version of it.
//
// WHY THIS DOES NOT USE MediaRecorder
// -----------------------------------
// MediaRecorder on Chrome and Edge emits WebM/Opus, and nothing in the server's
// audio stack can read it: libsndfile 1.2.2 has no WebM demuxer, so decoding
// fell through to an ffmpeg subprocess that is not installed on the dev machine
// (C:\ffmpeg\bin ships ffplay and ffprobe but no ffmpeg.exe). Every Chrome
// recording therefore failed to decode before the engine ever saw it, while the
// same recitation read from a .wav worked — exactly the reported symptom.
//
// Capturing PCM through Web Audio and writing the WAV ourselves removes the
// whole class of problem: no container negotiation, no codec, no transcode
// dependency, and the bytes the model sees are the bytes the microphone
// produced. It also matches the format the engine was measured on. The cost is
// a larger upload — 32 KB/s at 16 kHz mono, so the longest ayah in the Quran
// lands around 8 MB, inside the server's 12 MB limit.
const CONSTRAINTS: MediaStreamConstraints = {
  audio: {
    channelCount: 1,
    echoCancellation: false,
    noiseSuppression: false,
    autoGainControl: false,
  },
};

/** The engine's native rate. Browsers resample the mic feed to this for us. */
const TARGET_SR = 16000;

/**
 * Room tone captured before the caller is told recording is live. Gives the
 * server a genuine noise floor to measure against — without a moment of silence
 * somewhere in the clip, signal-to-noise is not a computable quantity.
 */
const SETTLE_MS = 300;

export type RecorderHandle = {
  stop: () => Promise<Blob>;
  cancel: () => void;
  /** Smoothed 0..1 loudness, for the breathing ring. */
  level: () => number;
  startedAt: number;
};

/**
 * Linear-interpolation resample to TARGET_SR.
 *
 * Only runs when the browser refused an AudioContext at 16 kHz (older Firefox,
 * some Android builds) and handed back 44.1 or 48 kHz instead. That used to be
 * harmless because takes were a few seconds; now that a whole ayah can be four
 * minutes, 48 kHz would mean a 23 MB upload for a recitation the engine is
 * going to downsample to 16 kHz anyway. Doing it here bounds the upload at
 * 32 KB/s whatever the device does.
 *
 * Linear interpolation is adequate because it is a DOWNsample to a rate the
 * model was measured at, and the browser has already low-passed the mic feed.
 */
function resample(input: Float32Array, from: number, to: number): Float32Array {
  if (from === to) return input;
  const ratio = from / to;
  const out = new Float32Array(Math.floor(input.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const pos = i * ratio;
    const j = Math.floor(pos);
    const frac = pos - j;
    const a = input[j];
    const b = j + 1 < input.length ? input[j + 1] : a;
    out[i] = a + (b - a) * frac;
  }
  return out;
}

/** Float32 PCM -> 16-bit mono WAV. */
function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buf);
  const str = (off: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i));
  };

  str(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  str(8, "WAVE");
  str(12, "fmt ");
  view.setUint32(16, 16, true); // PCM chunk size
  view.setUint16(20, 1, true); // format = PCM
  view.setUint16(22, 1, true); // channels
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  str(36, "data");
  view.setUint32(40, samples.length * 2, true);

  let off = 44;
  for (let i = 0; i < samples.length; i++, off += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buf], { type: "audio/wav" });
}

/** Worklet that forwards raw mono frames to the main thread. */
const WORKLET_SRC = `
class TapProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (ch && ch.length) this.port.postMessage(new Float32Array(ch));
    return true;
  }
}
registerProcessor('tap', TapProcessor);
`;

/* ══ THE HANDOFF ══════════════════════════════════════════════════════════
 *
 * WHY A MODULE-LEVEL SLOT AND NOT A PROP.
 *
 * The mic in the reader and the mic on the practice screen are the same
 * control, and pressing it has to start recording AT THE PRESS — not after the
 * app has resolved the ayah's practice range over the network and swapped
 * screens. Those are two different things and only one of them is allowed to
 * be slow.
 *
 * So the press does both at once: `startShared()` issues getUserMedia
 * immediately, and the range fetch runs beside it. Whichever screen mounts next
 * calls `claimShared()` and continues the recording that is already running,
 * rather than starting a second one. The component that started it has usually
 * unmounted by then, which is exactly why this cannot live in React state.
 *
 * THE PROMISE IS STORED, NOT THE HANDLE. `startRecording` takes a few hundred
 * milliseconds — a permission check, an AudioContext, and a deliberate settle
 * period that banks room tone. Parking the promise means the claimant can await
 * the same one instead of racing it or starting over.
 */
let pending: Promise<RecorderHandle> | null = null;

/** Begin now. The next screen picks this up; nothing is lost in between. */
export function startShared(): Promise<RecorderHandle> {
  cancelShared();
  pending = startRecording();
  // Nobody may be listening yet, and an unhandled rejection here would be a
  // console error on a denied microphone. The claimant re-awaits and handles it.
  pending.catch(() => {});
  return pending;
}

/** Take the in-flight recording, or null if this screen was reached some other way. */
export function claimShared(): Promise<RecorderHandle> | null {
  const p = pending;
  pending = null;
  return p;
}

/**
 * Drop it, and release the microphone with it.
 *
 * Called when the journey the recording was started for does not arrive — a
 * failed range fetch, or a second press. Without this the mic light stays on
 * after a navigation the learner has already abandoned, which is the single
 * worst bug this file could have.
 */
export function cancelShared(): void {
  pending?.then((h) => h.cancel()).catch(() => {});
  pending = null;
}

export async function startRecording(): Promise<RecorderHandle> {
  const stream = await navigator.mediaDevices.getUserMedia(CONSTRAINTS);

  // Asking for 16 kHz lets the browser do the resampling in native code. If it
  // declines (older Firefox), we record at whatever it gives and record the true
  // rate in the header — the server resamples from there.
  let ctx: AudioContext;
  try {
    ctx = new AudioContext({ sampleRate: TARGET_SR });
  } catch {
    ctx = new AudioContext();
  }
  if (ctx.state === "suspended") await ctx.resume();

  const source = ctx.createMediaStreamSource(stream);
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 1024;
  source.connect(analyser);
  const levelBuf = new Float32Array(analyser.fftSize);
  let smoothed = 0;

  const chunks: Float32Array[] = [];
  let total = 0;
  let detach = () => {};

  try {
    const url = URL.createObjectURL(
      new Blob([WORKLET_SRC], { type: "application/javascript" }),
    );
    await ctx.audioWorklet.addModule(url);
    URL.revokeObjectURL(url);
    const node = new AudioWorkletNode(ctx, "tap", {
      numberOfInputs: 1,
      numberOfOutputs: 0,
      channelCount: 1,
    });
    node.port.onmessage = (e: MessageEvent<Float32Array>) => {
      chunks.push(e.data);
      total += e.data.length;
    };
    source.connect(node);
    detach = () => {
      node.port.onmessage = null;
      source.disconnect(node);
    };
  } catch {
    // AudioWorklet unavailable (older Safari). ScriptProcessor is deprecated but
    // universally present, and it is the only remaining way to get raw PCM.
    const node = ctx.createScriptProcessor(4096, 1, 1);
    node.onaudioprocess = (e) => {
      const ch = e.inputBuffer.getChannelData(0);
      chunks.push(new Float32Array(ch));
      total += ch.length;
    };
    source.connect(node);
    // ScriptProcessor only fires while connected to a destination; route it into
    // a muted gain node so nothing is played back to the learner.
    const mute = ctx.createGain();
    mute.gain.value = 0;
    node.connect(mute);
    mute.connect(ctx.destination);
    detach = () => {
      node.onaudioprocess = null;
      source.disconnect(node);
      node.disconnect();
      mute.disconnect();
    };
  }

  const cleanup = () => {
    detach();
    stream.getTracks().forEach((t) => t.stop());
    ctx.close().catch(() => {});
  };

  // Let the mic settle and bank a little room tone before the UI goes live.
  await new Promise((r) => setTimeout(r, SETTLE_MS));

  return {
    startedAt: Date.now(),
    level: () => {
      analyser.getFloatTimeDomainData(levelBuf);
      let sum = 0;
      for (let i = 0; i < levelBuf.length; i++) sum += levelBuf[i] * levelBuf[i];
      const rms = Math.sqrt(sum / levelBuf.length);
      // Speech sits low in linear terms; map through a gentle curve so the ring
      // breathes rather than twitches.
      const shaped = Math.min(1, Math.sqrt(rms) * 2.6);
      smoothed += (shaped - smoothed) * 0.22;
      return smoothed;
    },
    stop: async () => {
      const rate = ctx.sampleRate;
      // Drain one more render quantum so the tail of the recitation is not cut.
      await new Promise((r) => setTimeout(r, 60));
      cleanup();
      const flat = new Float32Array(total);
      let off = 0;
      for (const c of chunks) {
        flat.set(c, off);
        off += c.length;
      }
      return encodeWav(resample(flat, rate, TARGET_SR), TARGET_SR);
    },
    cancel: cleanup,
  };
}
