"use client";

import { useEffect } from "react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // Surfaced in the server log; no user data is included in the digest.
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center bg-[var(--sbs-bg-page)]">
      <div className="sbs-container">
        <div className="flex max-w-[36rem] flex-col gap-5">
          <p className="sbs-eyebrow">Fehler</p>
          <h1 className="sbs-display--sm">Die Seite konnte nicht geladen werden.</h1>
          <p className="sbs-lead">
            Beim Aufbau dieser Seite ist ein Fehler aufgetreten. Ein erneuter Versuch hilft
            meistens; andernfalls erreichen Sie uns direkt.
          </p>
          {error.digest ? (
            <p className="sbs-mono text-[0.75rem] text-[var(--sbs-text-muted)]">Referenz: {error.digest}</p>
          ) : null}
          <div className="mt-2 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={reset}
              className="inline-flex min-h-11 items-center rounded-[var(--sbs-radius-md)] bg-[var(--sbs-accent)] px-5 text-[0.9375rem] font-[560] text-[var(--sbs-accent-contrast)]"
            >
              Erneut versuchen
            </button>
            {/* A full document load, not a client transition: this boundary
                renders when the router itself may be in a broken state. */}
            {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
            <a
              href="/"
              className="inline-flex min-h-11 items-center rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border-strong)] px-5 text-[0.9375rem] font-[560] text-[var(--sbs-text-primary)]"
            >
              Zur Startseite
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
