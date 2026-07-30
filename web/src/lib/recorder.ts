// Microphone capture with a live level read.
//
// Ask for the raw signal: browser AGC and noise suppression are tuned for phone
// calls, and they reshape exactly the spectral detail the tajweed engine
// measures. The server's quality gate should judge the real room, not a
// processed version of it.
const CONSTRAINTS: MediaStreamConstraints = {
  audio: {
    channelCount: 1,
    echoCancellation: false,
    noiseSuppression: false,
    autoGainControl: false,
  },
};

export type RecorderHandle = {
  stop: () => Promise<Blob>;
  cancel: () => void;
  /** Smoothed 0..1 loudness, for the breathing ring. */
  level: () => number;
  startedAt: number;
};

export async function startRecording(): Promise<RecorderHandle> {
  const stream = await navigator.mediaDevices.getUserMedia(CONSTRAINTS);
  const chunks: BlobPart[] = [];
  const rec = new MediaRecorder(stream);

  const ctx = new AudioContext();
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 1024;
  ctx.createMediaStreamSource(stream).connect(analyser);
  const buf = new Float32Array(analyser.fftSize);
  let smoothed = 0;

  rec.ondataavailable = (e) => e.data.size > 0 && chunks.push(e.data);
  rec.start();

  const cleanup = () => {
    stream.getTracks().forEach((t) => t.stop());
    ctx.close().catch(() => {});
  };

  return {
    startedAt: Date.now(),
    level: () => {
      analyser.getFloatTimeDomainData(buf);
      let sum = 0;
      for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
      const rms = Math.sqrt(sum / buf.length);
      // Speech sits low in linear terms; map through a gentle curve so the ring
      // breathes rather than twitches.
      const shaped = Math.min(1, Math.sqrt(rms) * 2.6);
      smoothed += (shaped - smoothed) * 0.22;
      return smoothed;
    },
    stop: () =>
      new Promise<Blob>((resolve) => {
        rec.onstop = () => {
          cleanup();
          resolve(new Blob(chunks, { type: rec.mimeType || "audio/webm" }));
        };
        rec.stop();
      }),
    cancel: () => {
      try {
        rec.stop();
      } catch {
        /* already stopped */
      }
      cleanup();
    },
  };
}
