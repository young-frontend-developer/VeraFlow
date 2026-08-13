import { useState } from "react";
import { Attempt } from "../lib/api";
import { Key, Lang, t } from "../lib/i18n";
import { weaknesses, progressPairs, timeBuckets, WeaknessEntry } from "../lib/weakness";
import { Blank } from "./States";
import { ArchOrnament } from "./Ornament";

const KIND_KEY: Record<string, Key> = {
  extra_letter: "kind_extra_letter",
  missing_letter: "kind_missing_letter",
  wrong_letter: "kind_wrong_letter",
  pronunciation: "kind_pronunciation",
  tajweed: "kind_tajweed",
  madd: "kind_madd",
  ghunna: "kind_ghunna",
  haraka: "kind_haraka",
  shadda: "kind_shadda",
};

const CAP = 5;
const MAX_LIST = 20;

function Sparkline({ buckets }: { buckets: { errorRate: number }[] }) {
  const max = Math.max(...buckets.map((b) => b.errorRate), 0.01);
  const w = 120;
  const h = 32;
  const barW = Math.min(12, (w - buckets.length) / buckets.length);
  const gap = buckets.length > 1 ? (w - barW * buckets.length) / (buckets.length - 1) : 0;

  return (
    <svg width={w} height={h} className="sparkline" aria-hidden="true">
      {buckets.slice(-8).map((b, i) => {
        const barH = Math.max(2, (b.errorRate / max) * (h - 2));
        return (
          <rect
            key={i}
            x={i * (barW + gap)}
            y={h - barH}
            width={barW}
            height={barH}
            rx={2}
            className="sparkline__bar"
          />
        );
      })}
    </svg>
  );
}

function WeaknessRow({
  entry,
  lang,
  progress,
  expanded,
  onToggle,
  onPractice,
  rows,
}: {
  entry: WeaknessEntry;
  lang: Lang;
  progress: { firstRate: number; latestRate: number; improving: boolean | null } | undefined;
  expanded: boolean;
  onToggle: () => void;
  onPractice: (sura: number, aya: number) => void;
  rows: Attempt[];
}) {
  const kindTitle = t(lang, KIND_KEY[entry.kind] ?? "kind_pronunciation");
  const buckets = expanded ? timeBuckets(rows, entry.code, entry.letter) : [];

  const arrow =
    progress?.improving === null
      ? { cls: "trend--neutral", label: t(lang, "weak_not_enough") }
      : progress?.improving
        ? { cls: "trend--down", label: t(lang, "weak_improving") }
        : { cls: "trend--up", label: t(lang, "weak_worsening") };

  return (
    <div className={`weakness-row ${expanded ? "weakness-row--open" : ""}`}>
      <button className="weakness-row__head" onClick={onToggle}>
        <span className="weakness-row__letter" lang="ar">{entry.letter}</span>
        <span className="weakness-row__info">
          <span className="weakness-row__kind">{kindTitle}</span>
          <span className="weakness-row__count">
            {t(lang, "weak_count").replace("{n}", String(entry.count))}
            {entry.recentCount > 0 && (
              <span className="weakness-row__recent">
                {" · "}{t(lang, "weak_recent").replace("{n}", String(entry.recentCount))}
              </span>
            )}
          </span>
        </span>
        <span className={`weakness-row__arrow ${arrow.cls}`}>
          {progress?.improving === null ? "—" : progress?.improving ? "↓" : "↑"}
        </span>
        {entry.isL1Pair && (
          <span className="weakness-row__l1">{t(lang, "weak_l1_label")}</span>
        )}
      </button>

      {expanded && (
        <div className="weakness-row__detail">
          {entry.content.headline && (
            <p className="weakness-row__headline">{entry.content.headline}</p>
          )}

          {progress && progress.improving !== null && (
            <p className="weakness-row__trend">
              {t(lang, "weak_first").replace("{n}", String(Math.round(progress.firstRate * 100)))}
              {" → "}
              {t(lang, "weak_latest").replace("{n}", String(Math.round(progress.latestRate * 100)))}
            </p>
          )}

          {entry.correctionRate > 0 && (
            <p className="weakness-row__rate">
              {t(lang, "weak_rate").replace("{n}", String(Math.round(entry.correctionRate * 100)))}
              {" · "}
              {t(lang, "weak_corrected").replace("{n}", String(entry.corrected))}
            </p>
          )}

          {buckets.length > 1 && <Sparkline buckets={buckets} />}

          {entry.content.fix && !entry.content.unauthored && (
            <p className="weakness-row__fix">{entry.content.fix}</p>
          )}
          {entry.ruleName && (
            <p className="weakness-row__rule">{entry.ruleName}</p>
          )}
          {entry.makhraj && (
            <p className="weakness-row__makhraj">
              {t(lang, "weak_makhraj")}: {entry.makhraj}
            </p>
          )}
          {entry.content.unauthored && (
            <p className="weakness-row__teacher">{t(lang, "weak_ask_teacher")}</p>
          )}

          {entry.content.audio_pair && (
            <button
              className="btn-quiet weakness-row__listen"
              onClick={() => new Audio(entry.content.audio_pair!).play()}
            >
              {t(lang, "weak_listen")}
            </button>
          )}

          <button
            className="btn-quiet weakness-row__practice"
            onClick={() => onPractice(entry.sura, entry.aya)}
          >
            {t(lang, "weak_lesson")}
          </button>
        </div>
      )}
    </div>
  );
}

export default function WeaknessBoard({
  lang,
  rows,
  onPractice,
}: {
  lang: Lang;
  rows: Attempt[];
  onPractice?: (sura: number, aya: number) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  const entries = weaknesses(rows);
  const progress = progressPairs(rows);
  const progressMap = new Map(progress.map((p) => [`${p.code}:${p.letter}`, p]));

  if (entries.length === 0) {
    return (
      <Blank
        title={t(lang, "weak_empty_title")}
        body={t(lang, "weak_empty_body")}
        ornament={<ArchOrnament className="blank__ornament" size={40} />}
      />
    );
  }

  const visible = showAll ? entries.slice(0, MAX_LIST) : entries.slice(0, CAP);

  return (
    <div className="weakness-board">
      <h3 className="section-subtitle">{t(lang, "weak_title")}</h3>
      {visible.map((entry) => {
        const key = `${entry.code}:${entry.letter}`;
        return (
          <WeaknessRow
            key={key}
            entry={entry}
            lang={lang}
            progress={progressMap.get(key)}
            expanded={expandedKey === key}
            onToggle={() => setExpandedKey(expandedKey === key ? null : key)}
            onPractice={onPractice ?? (() => {})}
            rows={rows}
          />
        );
      })}
      {entries.length > CAP && !showAll && (
        <button className="btn-quiet weakness-board__more" onClick={() => setShowAll(true)}>
          {t(lang, "weak_show_all")}
        </button>
      )}
    </div>
  );
}
