"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { useMotionCapable } from "@/lib/motion";
import { IndustryHeroGraphic } from "@/components/graphics/IndustryHeroGraphic";
import { LegalHeroGraphic } from "@/components/graphics/LegalHeroGraphic";
import { SbsNetworkGraphic } from "@/components/graphics/SbsNetworkGraphic";

/**
 * Hero slider for the corporate landing page.
 *
 * Purpose (§41: every animation states one): *orient*. The company runs two
 * divisions on one technical foundation, which is three things to say and no
 * room to say them at once. The slider says them in sequence instead of
 * shrinking all three into a grid nobody reads.
 *
 * Accessibility decisions worth keeping:
 *
 * - The page keeps exactly one `h1`, declared by the caller and never swapped.
 *   Slides carry `h2`s, so rotating content cannot rewrite the document's
 *   heading. A carousel that mutates the h1 breaks both outline and SEO.
 * - `aria-roledescription="carousel"` with `aria-live="off"` while playing:
 *   an auto-advancing region that announces itself is unusable with a screen
 *   reader. Live announcements switch on only once the reader takes manual
 *   control, which is when they are actually wanted.
 * - Auto-advance stops on hover, on focus inside, when the tab is hidden, and
 *   permanently as soon as the reader operates a control — taking over should
 *   never mean racing a timer.
 * - Under `prefers-reduced-motion: reduce` it never auto-advances and never
 *   animates the transition. The static state is the complete first slide with
 *   working controls, not a frozen fragment.
 * - Inactive slides are `inert`, so tabbing cannot reach an off-screen link.
 */

const AUTOPLAY_MS = 7000;

type Slide = {
  id: string;
  eyebrow: string;
  title: string;
  body: string;
  href: string;
  cta: string;
  graphic: (currentPath: string) => React.ReactNode;
};

const slides: Slide[] = [
  {
    id: "industrie",
    eyebrow: "SBS Industrie",
    title: "Technische Nachweise, die bis zur Fundstelle zurückführen",
    body: "Aus vorhandenen Prüfberichten, QM-Dokumenten und technischen Unterlagen entsteht eine Evidence Matrix — jede Zuordnung mit Quelle, Fundstelle, Modellversion und Prüfer.",
    href: "https://industrie.sbsdeutschland.com/",
    cta: "SBS Industrie ansehen",
    graphic: (p) => <IndustryHeroGraphic currentPath={p} />,
  },
  {
    id: "legal",
    eyebrow: "SBS Legal",
    title: "Vertrags- und Governance-Arbeit mit belegter Herkunft",
    body: "Klauseln, Fristen und Risiken werden extrahiert und verortet. Kein Ergebnis verlässt den Entwurfsstatus, bevor eine berechtigte Person es angenommen hat.",
    href: "https://legal.sbsdeutschland.com/",
    cta: "SBS Legal ansehen",
    graphic: () => <LegalHeroGraphic />,
  },
  {
    id: "plattform",
    eyebrow: "Gemeinsame Grundlage",
    title: "Eine Architektur, zwei Geschäftsbereiche",
    body: "Extraktion, Nachweisführung, Rollen, Freigabe und Protokoll funktionieren in beiden Bereichen gleich. Was sich unterscheidet, ist die Fachlichkeit — nicht die Nachvollziehbarkeit.",
    href: "/plattform",
    cta: "Plattform ansehen",
    graphic: (p) => <SbsNetworkGraphic currentPath={p} />,
  },
];

export function HeroSlider({ currentPath }: { currentPath: string }) {
  const [active, setActive] = useState(0);
  const [manual, setManual] = useState(false);
  const [paused, setPaused] = useState(false);
  const motionCapable = useMotionCapable();
  const regionRef = useRef<HTMLDivElement>(null);
  const baseId = useId();

  // The tab being hidden is not a reason to keep cycling.
  useEffect(() => {
    const onVisibility = () => setPaused(document.hidden);
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  const playing = motionCapable && !manual && !paused;

  useEffect(() => {
    if (!playing) return;
    const t = window.setTimeout(
      () => setActive((i) => (i + 1) % slides.length),
      AUTOPLAY_MS,
    );
    return () => window.clearTimeout(t);
  }, [playing, active]);

  const go = useCallback((next: number) => {
    setManual(true);
    setActive((next + slides.length) % slides.length);
  }, []);

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "ArrowRight") { event.preventDefault(); go(active + 1); }
    if (event.key === "ArrowLeft") { event.preventDefault(); go(active - 1); }
  };

  // Touch: a horizontal drag past the threshold moves one slide.
  const touchX = useRef<number | null>(null);
  const onTouchStart = (e: React.TouchEvent) => { touchX.current = e.touches[0].clientX; };
  const onTouchEnd = (e: React.TouchEvent) => {
    if (touchX.current === null) return;
    const dx = e.changedTouches[0].clientX - touchX.current;
    touchX.current = null;
    if (Math.abs(dx) > 48) go(active + (dx < 0 ? 1 : -1));
  };

  return (
    <div
      ref={regionRef}
      role="group"
      aria-roledescription="Karussell"
      aria-label="Geschäftsbereiche von SBS Deutschland"
      className="sbs-hero-slider"
      onKeyDown={onKeyDown}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) setPaused(false);
      }}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      <div className="sbs-hero-slider__viewport" aria-live={manual ? "polite" : "off"}>
        {slides.map((slide, index) => {
          const isActive = index === active;
          return (
            <div
              key={slide.id}
              id={`${baseId}-slide-${index}`}
              role="group"
              aria-roledescription="Folie"
              aria-label={`${index + 1} von ${slides.length}: ${slide.eyebrow}`}
              aria-hidden={!isActive}
              // React 19 renders `inert` from a boolean. It is what keeps an
              // off-screen slide's link out of the tab order; `visibility:
              // hidden` would too, but only for as long as nobody changes the
              // transition to one that keeps slides visible.
              inert={!isActive}
              className="sbs-hero-slider__slide"
              data-active={isActive ? "true" : "false"}
            >
              <div className="sbs-hero-slider__copy">
                <p className="sbs-eyebrow">{slide.eyebrow}</p>
                <h2 className="sbs-h3 sbs-hero-slider__title">{slide.title}</h2>
                <p className="sbs-lead">{slide.body}</p>
                <Link href={slide.href} className="sbs-hero-slider__cta">
                  {slide.cta}
                  <span aria-hidden="true" className="sbs-hero-slider__cta-arrow">→</span>
                </Link>
              </div>
              <div className="sbs-hero-slider__media">{slide.graphic(currentPath)}</div>
            </div>
          );
        })}
      </div>

      <div className="sbs-hero-slider__controls">
        <button
          type="button"
          className="sbs-hero-slider__arrow"
          onClick={() => go(active - 1)}
          aria-label="Vorherige Folie"
        >
          <span aria-hidden="true">←</span>
        </button>

        <ol className="sbs-hero-slider__dots">
          {slides.map((slide, index) => (
            <li key={slide.id}>
              <button
                type="button"
                className="sbs-hero-slider__dot"
                data-active={index === active ? "true" : "false"}
                aria-current={index === active ? "true" : undefined}
                aria-label={`Folie ${index + 1}: ${slide.eyebrow}`}
                onClick={() => go(index)}
              >
                <span className="sbs-hero-slider__dot-track">
                  <span
                    className="sbs-hero-slider__dot-fill"
                    data-running={index === active && playing ? "true" : "false"}
                    style={{ animationDuration: `${AUTOPLAY_MS}ms` }}
                  />
                </span>
                <span className="sbs-hero-slider__dot-label">{slide.eyebrow}</span>
              </button>
            </li>
          ))}
        </ol>

        <button
          type="button"
          className="sbs-hero-slider__arrow"
          onClick={() => go(active + 1)}
          aria-label="Nächste Folie"
        >
          <span aria-hidden="true">→</span>
        </button>
      </div>
    </div>
  );
}
