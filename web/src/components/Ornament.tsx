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
  // A MICROPHONE, because Practice is the record action and it is the centre
  // of the pill. It was an arch - the same mark the empty states use - which
  // said nothing about what the tab does.
  practice: icon(
    <>
      <rect x="7.4" y="3" width="5.2" height="9" rx="2.6" />
      <path d="M4.8 9.6a5.2 5.2 0 0 0 10.4 0" />
      <path d="M10 14.8v2.4" />
    </>,
  ),
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
  // A PERSON. The old mark was a circle with a plus through it, which reads as
  // "add" - the one thing this tab does not do.
  profile: icon(
    <>
      <circle cx="10" cy="7.3" r="3.1" />
      <path d="M4.4 16.6a5.6 5.6 0 0 1 11.2 0" />
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

/* ── top bar ──────────────────────────────────────────────────────────── */

export function Bookmark({ size = 18 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 18 18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.3"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4.5 2.5h9v13l-4.5-3.4-4.5 3.4z" />
    </svg>
  );
}

/* ── the daily plan ───────────────────────────────────────────────────── */
/* Hairline marks at the same weight as everything else, one per step. They
   carry no meaning the label does not already carry — they are there so the
   three cards scan as a set rather than as three paragraphs. */

export function PlanMemorize({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M2.5 3.2h4.2c.7 0 1.3.6 1.3 1.3v8.3c0-.6-.6-1.1-1.3-1.1H2.5z" />
      <path d="M13.5 3.2H9.3c-.7 0-1.3.6-1.3 1.3v8.3c0-.6.6-1.1 1.3-1.1h4.2z" />
    </svg>
  );
}

export function PlanRevise({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M13.2 8a5.2 5.2 0 1 1-1.6-3.7" />
      <path d="M13.4 2.6v3.1h-3.1" />
    </svg>
  );
}

export function PlanReflect({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="5.3" />
      <circle cx="8" cy="8" r="1.9" />
    </svg>
  );
}

/* ── OAuth marks ──────────────────────────────────────────────────────── */
/* Google's four-colour G and Apple's mark, drawn to their own brand
   specification rather than restyled into the app's palette — that is the one
   place the design system yields, because a recoloured provider mark is both a
   trademark problem and a recognition problem. The BUTTONS around them are
   ours; the marks are theirs. */

export function GoogleMark({ size = 17 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.9 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"
      />
    </svg>
  );
}

export function AppleMark({ size = 17 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12.3 9.6c0-1.86 1.52-2.75 1.59-2.8-.87-1.27-2.22-1.44-2.7-1.46-1.15-.12-2.24.67-2.83.67-.58 0-1.48-.65-2.43-.64-1.25.02-2.4.73-3.04 1.84-1.3 2.25-.33 5.58.93 7.4.62.9 1.35 1.9 2.31 1.86.93-.04 1.28-.6 2.4-.6 1.12 0 1.44.6 2.42.58 1-.02 1.63-.9 2.24-1.8.7-1.03.99-2.04 1-2.09-.02-.01-1.92-.74-1.94-2.92zM10.5 3.9c.51-.62.86-1.48.76-2.34-.74.03-1.63.49-2.16 1.11-.47.55-.89 1.43-.78 2.27.82.07 1.66-.42 2.18-1.04z"
      />
    </svg>
  );
}
