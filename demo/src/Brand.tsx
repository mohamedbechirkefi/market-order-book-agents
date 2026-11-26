// SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
// Brand marks, hero illustration and small motion helpers. The hero illustration is drawn from a
// fixed toy sequence; it is labelled "Illustration, not study data" and prints no number.
import { useEffect, useRef, useState, type RefObject } from "react";

// The mark: the letter M cut into five volume bars by a 45 degree V (public/brand/market-mark-*.svg).
const MARK_D =
  "M12 228 L12 28 L48 64 L48 228 Z M61 228 L61 77 L97 113 L97 228 Z M110 228 L110 126 L128 144 L146 126 L146 228 Z M159 228 L159 113 L195 77 L195 228 Z M208 228 L208 64 L244 28 L244 228 Z";

export function Mark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 256 256" aria-hidden="true" focusable="false">
      <path d={MARK_D} fill="currentColor" />
    </svg>
  );
}

export const reducedMotion = () => {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return true;
  }
};

/** Adds the class "is-in" once, the first time the element scrolls into view. Under reduced
 * motion, or without IntersectionObserver, the element is shown in its final state at once. */
export function useRevealOnce<T extends Element>(): [RefObject<T | null>, string] {
  const ref = useRef<T | null>(null);
  const [state, setState] = useState<"" | "reveal-armed" | "reveal-armed is-in">("");
  useEffect(() => {
    const el = ref.current;
    if (!el || reducedMotion() || typeof IntersectionObserver === "undefined") return;
    const r = el.getBoundingClientRect();
    if (r.top < window.innerHeight && r.bottom > 0) return; // already visible: no entrance
    setState("reveal-armed");
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setState("reveal-armed is-in");
          io.disconnect();
        }
      },
      { rootMargin: "0px 0px -12% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return [ref, state];
}

// ------------------------------------------------------------------ hero illustration

function mulberry32(a: number) {
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A fixed toy sequence of signed marks whose size clusters in bursts (illustration only):
 * a quiet base level plus three decaying bursts, times Gaussian noise. */
function tapeMarks(n: number): number[] {
  const rnd = mulberry32(20261126);
  const bursts = [0.16, 0.5, 0.8].map((f) => Math.round(f * n));
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    let v = 0.09;
    for (const c of bursts) if (i >= c) v += Math.exp(-(i - c) / 7);
    const u1 = Math.max(1e-9, rnd());
    const g = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * rnd());
    out.push(v * Math.max(-2.2, Math.min(2.2, g)));
  }
  const m = Math.max(...out.map(Math.abs));
  return out.map((x) => x / m);
}

const N_MARKS = 112;
const TAPE = tapeMarks(N_MARKS);
const LADDER = { asks: [0.42, 0.66, 0.5, 0.86, 0.58], bids: [0.54, 0.92, 0.62, 0.74, 0.4] };

export function HeroTape() {
  const W = N_MARKS * 10;
  return (
    <svg className="tape-svg" viewBox={`0 0 ${W} 120`} preserveAspectRatio="none" aria-hidden="true" focusable="false">
      <line x1="0" x2={W} y1="60" y2="60" className="tape-mid" />
      {TAPE.map((r, i) => {
        const h = Math.max(3, Math.abs(r) * 54);
        return (
          <rect
            key={i}
            className={r >= 0 ? "tm up" : "tm down"}
            x={i * 10 + 3}
            width="4"
            y={r >= 0 ? 60 - h : 60}
            height={h}
            style={{ animationDelay: `${300 + Math.floor(i / 2) * 30}ms`, transformOrigin: `${i * 10 + 5}px 60px` }}
          />
        );
      })}
    </svg>
  );
}

export function HeroLadder() {
  const rows = [
    ...[...LADDER.asks].reverse().map((w, i) => ({ side: "ask", w, order: 4 - i })),
    null,
    ...LADDER.bids.map((w, i) => ({ side: "bid", w, order: i })),
  ];
  return (
    <div className="hero-ladder" aria-hidden="true">
      {rows.map((r, i) =>
        r === null ? (
          <div key="spread" className="hl-spread">
            <span>spread</span>
          </div>
        ) : (
          <div key={i} className={`hl-row ${r.side}`}>
            <span className="hl-side">{r.side === "ask" ? "Ask" : "Bid"}</span>
            <span className="hl-track">
              <span className="hl-bar" style={{ width: `${r.w * 100}%`, animationDelay: `${120 + r.order * 40}ms` }} />
            </span>
          </div>
        ),
      )}
    </div>
  );
}

// ------------------------------------------------------------------ sticky navigation

export const SECTIONS = [
  { id: "overview", label: "Answer" },
  { id: "results", label: "Evidence" },
  { id: "exploratory", label: "Exploratory" },
  { id: "sandbox", label: "Sandbox" },
  { id: "method", label: "Method" },
];

export function TapeNav() {
  const list = useRef<HTMLUListElement | null>(null);
  const bar = useRef<HTMLSpanElement | null>(null);
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const seen = new Map<string, boolean>();
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) seen.set(e.target.id, e.isIntersecting);
        const first = SECTIONS.find((s) => seen.get(s.id));
        setActive(first ? first.id : null);
      },
      { rootMargin: "-30% 0px -60% 0px" },
    );
    const observe = () => SECTIONS.forEach((s) => { const el = document.getElementById(s.id); if (el) io.observe(el); });
    observe();
    const t = window.setTimeout(observe, 800); // sections that render after the results load
    return () => { io.disconnect(); window.clearTimeout(t); };
  }, []);

  useEffect(() => {
    const ul = list.current?.parentElement;
    const b = bar.current;
    if (!ul || !b) return;
    const a = active ? ul.querySelector<HTMLAnchorElement>(`a[href="#${active}"]`) : null;
    if (!a) { b.style.opacity = "0"; return; }
    b.style.opacity = "1";
    b.style.transform = `translateX(${a.offsetLeft}px) scaleX(${a.offsetWidth})`;
  }, [active]);

  return (
    <nav className="tapebar" aria-label="Sections">
      <div className="wrap tapebar-in">
        <a className="brand" href="#top" aria-label="MARKET, back to top">
          <Mark className="brand-mark" />
          <img className="brand-word" src="brand/market-wordmark-ink.svg" alt="" width="645" height="150" />
        </a>
        <div className="nav-track">
        <ul ref={list}>
          {SECTIONS.map((s) => (
            <li key={s.id}>
              <a href={`#${s.id}`} aria-current={active === s.id ? "true" : undefined}>
                {s.label}
              </a>
            </li>
          ))}
        </ul>
        <span ref={bar} className="nav-ind" aria-hidden="true" />
        </div>
      </div>
    </nav>
  );
}
