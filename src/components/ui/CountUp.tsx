"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Count-up figure. Purpose: *focus* — a number that moves is read; a number
 * that is simply printed is skimmed.
 *
 * The values it animates are counted from `src/content/*` at build time, never
 * written by hand, because §3 forbids invented figures. A count of what the
 * registry actually contains cannot drift away from the truth: add a product
 * and the number changes by itself.
 *
 * The final value is rendered on the server, so it is correct before any script
 * runs and correct if none ever does. The animation only replays the last
 * stretch of a number that was already there.
 */
export function CountUp({
  value,
  suffix = "",
  durationMs = 900,
}: {
  value: number;
  suffix?: string;
  durationMs?: number;
}) {
  const [shown, setShown] = useState(value);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;

    let frame = 0;
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting)) return;
        observer.disconnect();
        const start = performance.now();
        const tick = (now: number) => {
          const t = Math.min(1, (now - start) / durationMs);
          // easeOutCubic: fast first, settles precisely on the real value
          const eased = 1 - Math.pow(1 - t, 3);
          setShown(Math.round(eased * value));
          if (t < 1) frame = requestAnimationFrame(tick);
        };
        setShown(0);
        frame = requestAnimationFrame(tick);
      },
      { threshold: 0.4 },
    );

    observer.observe(node);
    return () => {
      observer.disconnect();
      if (frame) cancelAnimationFrame(frame);
    };
  }, [value, durationMs]);

  return (
    <span ref={ref} className="sbs-countup">
      {shown}
      {suffix}
    </span>
  );
}
