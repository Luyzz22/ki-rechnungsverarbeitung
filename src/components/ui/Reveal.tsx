"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { useMotionCapable } from "@/lib/motion";

/**
 * Scroll-triggered entrance. Purpose: *reveal* — sections announce themselves
 * as they come into reading position instead of all existing at once.
 *
 * It reveals once and then stops observing: content that re-animates every time
 * it scrolls past is a distraction, not a cue.
 *
 * The static state is the whole point of the component: if IntersectionObserver
 * is unavailable, or the reader prefers reduced motion, or JavaScript never
 * runs, the content is simply visible. `data-revealed` starts at "true" on the
 * server for exactly that reason — nothing is hidden until the client has
 * proven it can un-hide it.
 */
export function Reveal({
  children,
  as: Tag = "div",
  className = "",
}: {
  children: ReactNode;
  as?: "div" | "section";
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const motionCapable = useMotionCapable();
  const [seen, setSeen] = useState(false);

  // Hidden only when this client can also un-hide it, and only until it has.
  const revealed = !motionCapable || seen;

  useEffect(() => {
    const node = ref.current;
    if (!node || !motionCapable || seen) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setSeen(true);
            observer.disconnect();
          }
        }
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.08 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [motionCapable, seen]);

  return (
    <Tag
      ref={ref as React.Ref<HTMLDivElement & HTMLElement>}
      className={`sbs-reveal-wrap ${className}`}
      data-revealed={revealed ? "true" : "false"}
    >
      {children}
    </Tag>
  );
}
