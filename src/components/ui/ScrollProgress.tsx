"use client";

import { useEffect, useState } from "react";
import { useMotionCapable } from "@/lib/motion";

/**
 * Reading progress along the top edge. Purpose: *orient* — long pages give no
 * sense of how much is left, and a scrollbar is easy to miss on a trackpad.
 *
 * Presentational only: `aria-hidden`, because the information it carries is
 * already available to assistive technology through the scroll position itself.
 * It renders nothing under reduced motion rather than sitting there frozen.
 */
export function ScrollProgress() {
  const [progress, setProgress] = useState(0);
  const enabled = useMotionCapable();

  useEffect(() => {
    if (!enabled) return;

    let frame = 0;
    const update = () => {
      frame = 0;
      const scrollable = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(scrollable > 0 ? Math.min(1, window.scrollY / scrollable) : 0);
    };
    const onScroll = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(update);
    };

    // Scheduled rather than called: the first measurement belongs in a frame
    // callback, not in the effect body.
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [enabled]);

  if (!enabled) return null;

  return (
    <div className="sbs-scroll-progress" aria-hidden="true">
      <div className="sbs-scroll-progress__bar" style={{ transform: `scaleX(${progress})` }} />
    </div>
  );
}
