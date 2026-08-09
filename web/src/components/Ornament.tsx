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

/**
 * FIVE ICONS THAT ARE NOT THE STOCK FIVE.
 *
 * Every app in this category ships a house, an open book, a bar chart and a
 * graduation cap, and the result is that they are all recognisably the same
 * app. These are drawn from the same Timurid vocabulary as the ornaments above,
 * on the same 20px grid at the same hairline weight, so the row reads as one
 * hand — and so the nav belongs to this app rather than to the icon pack.
 *
 *   home      a mihrab arch under a lintel — the niche you stand in
 *   practice  an open mushaf with the ayah rule down its centre
 *   tutor     a microphone. The one literal glyph in the set, because the
 *             centre button must not be a puzzle
 *   progress  a rising path with the eight-point star at its summit
 *   learn     a hanging qandil — the mosque lamp, which is what "learning"
 *             looks like in this visual tradition and not what it looks like
 *             in a stock icon set
 */
export const TabIcon = {
  home: icon(
    <>
      <path d="M4.2 16.8V9.4a5.8 5.8 0 0 1 11.6 0v7.4" />
      <path d="M7.6 16.8v-7a2.4 2.4 0 0 1 4.8 0v7" />
      <path d="M2.8 16.8h14.4" />
    </>,
  ),
  practice: icon(
    <>
      <path d="M10 5.4v10.2" />
      <path d="M10 5.4c-1.6-1-3.4-1.3-5.7-1.2v9.9c2.3-.1 4.1.2 5.7 1.2" />
      <path d="M10 5.4c1.6-1 3.4-1.3 5.7-1.2v9.9c-2.3-.1-4.1.2-5.7 1.2" />
    </>,
  ),
  // A MICROPHONE, because the centre is the record action. Kept literal on
  // purpose: it is the one control the whole bar is arranged around.
  tutor: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="9" y="3" width="6" height="10.4" rx="3" />
      <path d="M5.6 11.4a6.4 6.4 0 0 0 12.8 0" />
      <path d="M12 17.8v3" />
    </svg>
  ),
  progress: icon(
    <>
      <path d="M3 15.4l3.6-3.9 2.8 2.2 3.4-4.5" />
      <path d="M15.4 4.2l1.1 2.2 2.2 1.1-2.2 1.1-1.1 2.2-1.1-2.2-2.2-1.1 2.2-1.1z" />
    </>,
  ),
  // A QALAM — THE CUT REED. Third attempt, and this one is subtractive.
  //
  // ── WHY THE PREVIOUS TWO READ AS A BALLPOINT ────────────────────────────
  //
  // Not because they were drawn as pens. They were drawn as reeds, with a
  // chisel nib, a slit and a node ring, and every one of those details is
  // correct about a real qalam. Rendered at 320px the drawing is a qalam.
  // Rendered at 20px, which is the only size it is ever seen at, seven
  // hairline strokes inside a 20-unit box do this:
  //
  //   the shaft's two parallel lines sat 2.3 units apart at stroke 1.3, so the
  //     1-unit gap between them closed up and the tube filled in SOLID
  //   the node — one short stroke across the barrel — survived as the only
  //     readable interior detail, and a short bar across a pen barrel is
  //     universally a POCKET CLIP
  //   the slit and the nib wedge merged into one fat paddle
  //
  // A solid barrel with a clip is a marker pen. The detail was not wrong, it
  // was invisible, and what remained of it was worse than nothing.
  //
  // ── WHAT THIS IS ────────────────────────────────────────────────────────
  //
  // ONE closed outline and no interior strokes at all: a long slender rod on
  // the diagonal, square-cut at the top end, and cut OBLIQUELY at the bottom
  // so one side runs 3.5 units further than the other and meets the short side
  // at a point. That oblique face is the nib — it is the whole reason Arabic
  // script has thick and thin strokes — and at 20px it is the only thing that
  // has to survive, so it is the only thing drawn.
  //
  // The rod is 3.2 units wide against a 1.3 stroke, which leaves 1.9 units of
  // open interior: it reads as a hollow stalk rather than a filled bar. It is
  // 15 units long, so the proportion is a reed rather than a blade. Miter
  // joins rather than the set's round ones, and only here — a rounded-off
  // point is not a cut, and the cut is the entire icon.
  //
  // No node, no slit, no baseline. Each of those was true and each of them, at
  // this size, cost more than it carried.
  learn: icon(
    <path
      d="M14.2 4.7 16.4 7 8.3 15.1 3.6 15.3Z"
      strokeLinejoin="miter"
      strokeLinecap="butt"
    />,
  ),
  // A PERSON. Not in the bar any more - it lives behind the settings gear -
  // but Profile still labels itself with it.
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

/** Leave. Not "back" — this exits practice entirely, to the sura list. */
export function Close({ size = 17 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M4 4l8 8M12 4l-8 8" />
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

/* ── the progress marks ─────────────────────────────────────────────────── */
/* Streak, hasanat, ayat and time. Four glyphs at one weight on one grid, so
   the stat row reads as a set rather than as four borrowed pictograms.

   NOTE ON THE FLAME. A flame is the one conventional glyph in here and it is
   used knowingly: a streak is a widely understood idea and inventing a private
   symbol for it would make the card a riddle. It is drawn as a single hairline
   contour rather than as a filled emoji-style blob, which is what keeps it in
   the same family as the rest. */

const mark = (size: number, children: React.ReactNode) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.35"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);

export function Flame({ size = 20 }: { size?: number }) {
  return mark(
    size,
    <>
      <path d="M12 3.2c3.4 3 5.4 5.6 5.4 8.6a5.4 5.4 0 0 1-10.8 0c0-1.4.5-2.6 1.5-3.8.3 1.1.9 1.8 1.7 2.1.4-2.6.8-4.7 2.2-6.9z" />
      <path d="M12 20.4a2.6 2.6 0 0 1-2.6-2.6c0-1.3.9-2.2 2.6-3.8 1.7 1.6 2.6 2.5 2.6 3.8a2.6 2.6 0 0 1-2.6 2.6z" />
    </>,
  );
}

/** Hasanat. The eight-point star at its smallest, with a spark of light. */
export function Sparkle({ size = 20 }: { size?: number }) {
  return mark(
    size,
    <>
      <path d="M12 3.4l1.9 4.1 4.1 1.9-4.1 1.9-1.9 4.1-1.9-4.1L6 9.4l4.1-1.9z" />
      <path d="M18.2 15.4l.8 1.7 1.7.8-1.7.8-.8 1.7-.8-1.7-1.7-.8 1.7-.8z" />
    </>,
  );
}

/** Ayat completed. A folded page with the ayah rule across it. */
export function Leaf({ size = 20 }: { size?: number }) {
  return mark(
    size,
    <>
      <path d="M6 3.6h7.4L18 8.2v12.2H6z" />
      <path d="M13.4 3.6v4.6H18" />
      <path d="M9 12.6h6M9 16.2h4" />
    </>,
  );
}

/** Time practised. A dial, not a stopwatch — nothing here is being raced. */
export function Dial({ size = 20 }: { size?: number }) {
  return mark(
    size,
    <>
      <circle cx="12" cy="12" r="8.4" />
      <path d="M12 7.2V12l3.2 2" />
    </>,
  );
}

/* ── the weekly activity glyphs ─────────────────────────────────────────── */
/* Three states, three DIFFERENT SHAPES — never one shape in three colours. A
   week strip whose only difference is hue is unreadable to anyone who cannot
   separate the hues, and this one is read at a glance in a row of seven.

   And no faces. A missed day drawn as a sad face is the app editorialising
   about someone's week; an open ring says the same fact and says nothing
   about them. */

export function DayDone({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.16" />
      <circle
        cx="12"
        cy="12"
        r="10"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
      />
      <path
        d="M7.6 12.4 10.6 15.4 16.4 8.8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function DayMissed({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <circle
        cx="12"
        cy="12"
        r="10"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeDasharray="2.6 3.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function DayPending({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <circle
        cx="12"
        cy="12"
        r="10"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      <circle cx="12" cy="12" r="2.6" fill="currentColor" />
    </svg>
  );
}

/* ── the tutor's mark ───────────────────────────────────────────────────── */

/**
 * WHAT STANDS IN FOR THE TEACHER.
 *
 * Not a face. Not an illustrated one, not a generated one, not a friendly
 * abstract blob with eyes. This app puts a geometric mark wherever a product
 * like it would put a headshot, and the rule holds hardest here, on the card
 * that introduces guidance: a face beside a correction implies a person has
 * looked at your recitation and formed an opinion of you, and no person has.
 *
 * So the tutor is a light. An eight-point khatam with a calligraphic stroke
 * turning through it — the pen mark and the star, which is what this app
 * actually is — set inside a ring that glows. It reads as a presence without
 * pretending to be one.
 */
export function TutorMark({ size = 56 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <radialGradient id="tutor-bloom" cx="50%" cy="42%" r="52%">
          <stop offset="0%" stopColor="#ecca85" stopOpacity="0.42" />
          <stop offset="100%" stopColor="#d4a853" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="32" cy="32" r="30" fill="url(#tutor-bloom)" />
      <circle
        cx="32"
        cy="32"
        r="25"
        stroke="currentColor"
        strokeWidth="0.9"
        opacity="0.4"
      />
      {/* the khatam */}
      <g stroke="currentColor" strokeWidth="1.1" opacity="0.75">
        <rect x="20" y="20" width="24" height="24" />
        <rect x="20" y="20" width="24" height="24" transform="rotate(45 32 32)" />
      </g>
      {/* the calligraphic turn — one stroke, thick to thin, as a qalam makes */}
      <path
        d="M20.5 38.5c4.6 4.2 10.4 5.2 15.6 2.6 4.4-2.2 6.4-6.4 5-10.2-1.1-3-4.2-4.4-6.6-3.2-2 1-2.6 3.2-1.4 4.8 1 1.3 2.8 1.5 3.9.5"
        stroke="currentColor"
        strokeWidth="2.1"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/* ── top bar ──────────────────────────────────────────────────────────── */

/**
 * Settings. Where Profile lives now that it is out of the tab row.
 *
 * A CLOSED COG, not a hub with spokes. The first version drew eight radiating
 * strokes around a circle, which at 18px on a dark ground is not a gear — it is
 * a sun, and it sat in the corner of a screen that already has a brass glow
 * theme. The teeth are drawn as a single closed outline so the silhouette reads
 * at a glance instead of resolving into rays.
 */
/**
 * The notification bell.
 *
 * A QANDIL, NOT A HANDBELL. The mosque lamp hangs by a chain from an arch and
 * flares at the base, which is the same silhouette a bell icon has and a
 * shape this app already owns — the ornaments upstairs are drawn from the same
 * vocabulary. A stock jingle-bell with a clapper would be the one glyph in the
 * top bar borrowed from a generic icon set, three centimetres from the
 * wordmark.
 *
 * The clapper stroke at the bottom is kept, because without it the shape is a
 * lamp and with it the shape is a bell — and this control must be recognised
 * as notifications on the first look, not admired for its provenance.
 */
export function Bell({ size = 19 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.35"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {/* The hanging ring. */}
      <path d="M10 2.1v1.4" />
      {/* The body: shoulders rising to a dome, skirt flaring to the rim. */}
      <path d="M10 3.5a4.6 4.6 0 0 0-4.6 4.6c0 3.1-.7 4.6-1.6 5.5h12.4c-.9-.9-1.6-2.4-1.6-5.5A4.6 4.6 0 0 0 10 3.5z" />
      {/* The clapper. */}
      <path d="M8.4 15.6a1.9 1.9 0 0 0 3.2 0" />
    </svg>
  );
}

/** A target with an arrow in it — goals. Drawn on the icon set's 20px grid. */
export function Target({ size = 20 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.3"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="10" cy="10" r="7.1" />
      <circle cx="10" cy="10" r="3.6" />
      <circle cx="10" cy="10" r="0.9" />
    </svg>
  );
}

export function Gear({ size = 18 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.25"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M8.6 2.2h2.8l.35 1.9 1.5.87 1.8-.67 1.4 2.42-1.45 1.26v1.74l1.45 1.26-1.4 2.42-1.8-.67-1.5.87-.35 1.9H8.6l-.35-1.9-1.5-.87-1.8.67-1.4-2.42 1.45-1.26V8.98L3.55 7.72l1.4-2.42 1.8.67 1.5-.87z" />
      <circle cx="10" cy="10" r="2.5" />
    </svg>
  );
}

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
