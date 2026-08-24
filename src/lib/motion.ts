"use client";

import { useSyncExternalStore } from "react";

/**
 * Whether this client may animate: it has the APIs and the reader has not asked
 * for reduced motion.
 *
 * `useSyncExternalStore` rather than `useState` + `useEffect`, because that is
 * what a media query is — an external store with a snapshot and a subscription.
 * Reading it in an effect and calling `setState` would render once with the
 * wrong answer and then correct itself, which is both a flash and a lint error.
 *
 * The server snapshot is `false`. Markup therefore renders in its static,
 * fully-visible form, and animation is only ever added by a client that has
 * proved it can also take it away.
 */

function subscribe(onChange: () => void) {
  if (typeof window === "undefined" || !window.matchMedia) return () => {};
  const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
  mq.addEventListener("change", onChange);
  return () => mq.removeEventListener("change", onChange);
}

function getSnapshot() {
  if (typeof window === "undefined") return false;
  if (typeof IntersectionObserver === "undefined") return false;
  if (!window.matchMedia) return false;
  return !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function getServerSnapshot() {
  return false;
}

export function useMotionCapable() {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
