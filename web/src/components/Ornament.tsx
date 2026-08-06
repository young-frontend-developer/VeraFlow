/**
 * The app's marks and icons, in one place so they cannot drift apart.
 *
 * WHY THESE AND NOT PHOTOGRAPHS. Wherever a product like this would normally
 * put a scholar's headshot or a reciter's portrait, Tilawah puts a geometric
 * mark instead. That is a consent rule, not a style preference: a face beside
 * a recitation implies a person has endorsed it, and no one has. Nothing here
 * depicts a person, real or generated.
 *
 * The ornaments are Timurid-derived geometry — an eight-point star, a pointed
 * arch, an interlace — drawn at hairline weight in the sage accent so they sit
 * at the same visual volume as the rules on the page. They are drawn rather
 * than imported: three shapes is not worth a dependency, and an icon pack
 * would arrive at its own stroke weight and quietly break the one system.
 */

type Props = { className?: string; size?: number };

const svg = (size: number, children: React.ReactNode) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 48 48"
    fill="none"
    stroke="currentColor"
    strokeWidth="1"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);

/** Eight-point star — the girih figure. The app's quiet signature. */
export function StarOrnament({ className, size = 48 }: Props) {
  return (
    <span className={className}>
      {svg(
        size,
        <>
          <rect x="12" y="12" width="24" height="24" transform="rotate(45 24 24)" />
          <rect x="12" y="12" width="24" height="24" />
          <circle cx="24" cy="24" r="5.5" />
        </>,
      )}
    </span>
  );
}

/** A pointed arch — the niche you stand in to recite. */
export function ArchOrnament({ className, size = 48 }: Props) {
  return (
    <span className={className}>
      {svg(
        size,
        <>
          <path d="M11 40V24c0-7.2 5.8-13 13-13s13 5.8 13 13v16" />
          <path d="M17 40V25a7 7 0 0 1 14 0v15" />
          <path d="M8 40h32" />
        </>,
      )}
    </span>
  );
}

/** An open book — reading, and the Learn tab. */
export function BookOrnament({ className, size = 48 }: Props) {
  return (
    <span className={className}>
      {svg(
        size,
        <>
          <path d="M24 14v24" />
          <path d="M24 14c-3.6-2.4-8-3.2-14-3v23c6-.2 10.4.6 14 3" />
          <path d="M24 14c3.6-2.4 8-3.2 14-3v23c-6-.2-10.4.6-14 3" />
        </>,
      )}
    </span>
  );
}

/** Interlace — repetition returning on itself. The Memorize tab. */
export function KnotOrnament({ className, size = 48 }: Props) {
  return (
    <span className={className}>
      {svg(
        size,
        <>
          <circle cx="18" cy="24" r="9" />
          <circle cx="30" cy="24" r="9" />
          <path d="M24 12v24" />
        </>,
      )}
    </span>
  );
}

/* ── tab bar icons. 20px, hairline, drawn on the same grid. ─────────────── */

const icon = (children: React.ReactNode) => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 20 20"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.3"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);

export const TabIcon = {
  today: icon(
    <>
      <circle cx="10" cy="10" r="6.8" />
      <path d="M10 6.2V10l2.6 1.6" />
    </>,
  ),
  practice: icon(<path d="M4 16.5V9.5a6 6 0 0 1 12 0v7" />),
  learn: icon(
    <>
      <path d="M10 5.6v9.8" />
      <path d="M10 5.6c-1.5-.9-3.2-1.2-5.4-1.1v9.4c2.2-.1 3.9.2 5.4 1.1" />
      <path d="M10 5.6c1.5-.9 3.2-1.2 5.4-1.1v9.4c-2.2-.1-3.9.2-5.4 1.1" />
    </>,
  ),
  memorize: icon(
    <>
      <circle cx="7.6" cy="10" r="4.4" />
      <circle cx="12.4" cy="10" r="4.4" />
    </>,
  ),
  profile: icon(
    <>
      <circle cx="10" cy="10" r="7" />
      <path d="M10 6.4v7.2M6.4 10h7.2" />
    </>,
  ),
} as const;

/* ── small inline glyphs ────────────────────────────────────────────────── */

export function Play({ size = 11 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 12 12"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M3 1.6 10 6 3 10.4Z" />
    </svg>
  );
}

export function Pause({ size = 11 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 12 12"
      fill="currentColor"
      aria-hidden="true"
    >
      <rect x="2.5" y="1.5" width="2.6" height="9" rx="0.6" />
      <rect x="6.9" y="1.5" width="2.6" height="9" rx="0.6" />
    </svg>
  );
}

export function Mic({ size = 26 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="9" y="2.6" width="6" height="11" rx="3" />
      <path d="M5.4 11.2a6.6 6.6 0 0 0 13.2 0" />
      <path d="M12 17.8v3.6" />
    </svg>
  );
}

export function Stop({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <rect x="7" y="7" width="10" height="10" rx="2.4" />
    </svg>
  );
}

export function Chevron({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.3"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 3.5 10.5 8 6 12.5" />
    </svg>
  );
}

export function Tick({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3.5 8.4 6.6 11.5 12.5 4.8" />
    </svg>
  );
}
