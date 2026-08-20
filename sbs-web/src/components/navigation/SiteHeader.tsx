"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { NavItem } from "@/lib/nav";
import { linkFor, type SiteConfig } from "@/content/site";
import { Wordmark } from "./Wordmark";
import { MegaPanelGraphic } from "./MegaPanelGraphic";
import { Button } from "@/components/ui/Button";

type Props = {
  site: SiteConfig;
  nav: NavItem[];
  cta: { label: string; href: string };
  homeHref: string;
  /** Route the header is rendered on; decides relative vs cross-site hrefs. */
  currentPath: string;
  /** Shown on the division sites so the way back to corporate is always one click. */
  parentLink?: { label: string; href: string };
};

export function SiteHeader({ site, nav, cta, homeHref, currentPath, parentLink }: Props) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const headerRef = useRef<HTMLElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const baseId = useId();

  const close = useCallback(() => setOpenIndex(null), []);

  // Purpose: orient — a hairline appears once the page has moved.
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (openIndex === null && !mobileOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (mobileOpen) setMobileOpen(false);
      else close();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [openIndex, mobileOpen, close]);

  // Clicking or focusing outside the header dismisses the mega menu.
  useEffect(() => {
    if (openIndex === null) return;
    const onOutside = (event: Event) => {
      if (!headerRef.current?.contains(event.target as Node)) close();
    };
    document.addEventListener("pointerdown", onOutside);
    document.addEventListener("focusin", onOutside);
    return () => {
      document.removeEventListener("pointerdown", onOutside);
      document.removeEventListener("focusin", onOutside);
    };
  }, [openIndex, close]);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  const openWithDelay = (index: number) => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    setOpenIndex(index);
  };

  const closeWithDelay = () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    closeTimer.current = setTimeout(() => setOpenIndex(null), 120);
  };

  return (
    <header
      ref={headerRef}
      className={`sticky top-0 z-50 bg-[var(--sbs-bg-page)]/92 backdrop-blur-[10px] transition-[border-color,box-shadow] duration-[var(--sbs-motion-normal)] ${
        scrolled || openIndex !== null
          ? "border-b border-[var(--sbs-border-subtle)] shadow-[var(--sbs-shadow-sm)]"
          : "border-b border-transparent"
      }`}
      onMouseLeave={closeWithDelay}
    >
      <div className="sbs-container">
        <div className="flex h-[var(--sbs-header-height)] items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <Wordmark site={site} homeHref={linkFor(currentPath, homeHref)} />
          </div>

          <nav aria-label="Hauptnavigation" className="hidden lg:block">
            <ul className="flex items-center gap-1">
              {nav.map((item, index) => {
                const panelId = `${baseId}-panel-${index}`;
                if (!item.columns) {
                  return (
                    <li key={item.label}>
                      <Link
                        href={linkFor(currentPath, item.href ?? "/")}
                        className="inline-flex min-h-11 items-center rounded-[var(--sbs-radius-sm)] px-3 text-[0.9375rem] font-[540] text-[var(--sbs-text-secondary)] transition-colors duration-[var(--sbs-motion-fast)] hover:text-[var(--sbs-text-primary)]"
                      >
                        {item.label}
                      </Link>
                    </li>
                  );
                }
                const open = openIndex === index;
                return (
                  <li key={item.label} onMouseEnter={() => openWithDelay(index)}>
                    <button
                      type="button"
                      aria-expanded={open}
                      aria-controls={panelId}
                      onClick={() => setOpenIndex(open ? null : index)}
                      className={`inline-flex min-h-11 items-center gap-1.5 rounded-[var(--sbs-radius-sm)] px-3 text-[0.9375rem] font-[540] transition-colors duration-[var(--sbs-motion-fast)] ${
                        open ? "text-[var(--sbs-text-primary)]" : "text-[var(--sbs-text-secondary)] hover:text-[var(--sbs-text-primary)]"
                      }`}
                    >
                      {item.label}
                      <Chevron open={open} />
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>

          <div className="flex items-center gap-2">
            {parentLink ? (
              <Link
                href={linkFor(currentPath, parentLink.href)}
                className="hidden min-h-11 items-center rounded-[var(--sbs-radius-sm)] px-3 text-[0.875rem] font-[500] text-[var(--sbs-text-muted)] transition-colors duration-[var(--sbs-motion-fast)] hover:text-[var(--sbs-text-primary)] lg:inline-flex"
              >
                {parentLink.label}
              </Link>
            ) : null}
            <div className="hidden sm:block">
              <Button href={linkFor(currentPath, cta.href)} size="md">
                {cta.label}
              </Button>
            </div>
            <button
              type="button"
              className="inline-flex h-11 w-11 items-center justify-center rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] text-[var(--sbs-text-primary)] lg:hidden"
              aria-expanded={mobileOpen}
              aria-controls={`${baseId}-mobile`}
              onClick={() => setMobileOpen((value) => !value)}
            >
              <span className="sr-only">{mobileOpen ? "Menü schließen" : "Menü öffnen"}</span>
              <Burger open={mobileOpen} />
            </button>
          </div>
        </div>
      </div>

      {/* Desktop mega menu */}
      {nav.map((item, index) => {
        if (!item.columns) return null;
        const open = openIndex === index;
        return (
          <div
            key={item.label}
            id={`${baseId}-panel-${index}`}
            hidden={!open}
            className="absolute inset-x-0 top-full hidden border-b border-[var(--sbs-border-subtle)] bg-[var(--sbs-bg-page)] shadow-[var(--sbs-shadow-lg)] lg:block"
            style={open ? { animation: "sbs-menu-in var(--sbs-motion-normal) var(--sbs-ease-standard) both" } : undefined}
            onMouseEnter={() => openWithDelay(index)}
          >
            <div className="sbs-container py-8">
              <div className={`grid gap-8 ${item.featured ? "lg:grid-cols-[1fr_1fr_1fr_minmax(0,17rem)]" : "lg:grid-cols-3"}`}>
                {item.columns.map((column) => (
                  <div key={column.title}>
                    <p className="sbs-eyebrow mb-3 text-[var(--sbs-text-muted)]">{column.title}</p>
                    <ul className="flex flex-col gap-0.5">
                      {column.links.map((link) => (
                        <li key={`${column.title}-${link.href}-${link.label}`}>
                          <Link
                            href={linkFor(currentPath, link.href)}
                            onClick={close}
                            className="group block rounded-[var(--sbs-radius-md)] px-2 py-2 -mx-2 transition-colors duration-[var(--sbs-motion-fast)] hover:bg-[var(--sbs-bg-sunken)]"
                          >
                            <span className="block text-[0.9375rem] font-[560] text-[var(--sbs-text-primary)] group-hover:text-[var(--sbs-accent-strong)]">
                              {link.label}
                            </span>
                            {link.description ? (
                              <span className="mt-0.5 block text-[0.8125rem] leading-[1.45] text-[var(--sbs-text-muted)]">
                                {link.description}
                              </span>
                            ) : null}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
                {item.featured ? (
                  <Link
                    href={linkFor(currentPath, item.featured.href)}
                    onClick={close}
                    className="group flex flex-col gap-3 rounded-[var(--sbs-radius-lg)] border border-[var(--sbs-border-subtle)] bg-[var(--sbs-bg-sunken)] p-5 transition-colors duration-[var(--sbs-motion-fast)] hover:border-[var(--sbs-accent)]"
                  >
                    <MegaPanelGraphic variant={item.featured.graphic} />
                    <div>
                      <p className="sbs-eyebrow">{item.featured.eyebrow}</p>
                      <p className="mt-1 text-[0.9375rem] font-[600] text-[var(--sbs-text-primary)]">
                        {item.featured.title}
                      </p>
                      <p className="mt-1 text-[0.8125rem] leading-[1.45] text-[var(--sbs-text-secondary)]">
                        {item.featured.body}
                      </p>
                    </div>
                  </Link>
                ) : null}
              </div>
            </div>
          </div>
        );
      })}

      {/* Mobile drawer */}
      <div
        id={`${baseId}-mobile`}
        hidden={!mobileOpen}
        className="fixed inset-x-0 bottom-0 top-[var(--sbs-header-height)] z-40 overflow-y-auto overscroll-contain border-t border-[var(--sbs-border-subtle)] bg-[var(--sbs-bg-page)] lg:hidden"
      >
        <div className="sbs-container flex flex-col gap-7 py-7 pb-16">
          {nav.map((item) => (
            <nav key={item.label} aria-label={item.label}>
              <div className="flex items-baseline justify-between gap-3 border-b border-[var(--sbs-border-subtle)] pb-2">
                <p className="text-[0.9375rem] font-[640] text-[var(--sbs-text-primary)]">{item.label}</p>
                {item.href ? (
                  <Link
                    href={linkFor(currentPath, item.href)}
                    onClick={() => setMobileOpen(false)}
                    className="text-[0.8125rem] font-[540] text-[var(--sbs-accent)]"
                  >
                    Übersicht
                  </Link>
                ) : null}
              </div>
              {item.columns ? (
                <div className="mt-3 flex flex-col gap-5">
                  {item.columns.map((column) => (
                    <div key={column.title}>
                      <p className="sbs-eyebrow mb-2 text-[var(--sbs-text-muted)]">{column.title}</p>
                      <ul className="flex flex-col">
                        {column.links.map((link) => (
                          <li key={`${column.title}-${link.href}-${link.label}`}>
                            <Link
                              href={linkFor(currentPath, link.href)}
                              onClick={() => setMobileOpen(false)}
                              className="flex min-h-11 items-center text-[0.9375rem] text-[var(--sbs-text-secondary)]"
                            >
                              {link.label}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              ) : null}
            </nav>
          ))}
          <div className="flex flex-col gap-3 pt-2">
            <Button href={linkFor(currentPath, cta.href)} size="lg" className="w-full">
              {cta.label}
            </Button>
            {parentLink ? (
              <Button href={linkFor(currentPath, parentLink.href)} variant="secondary" size="lg" className="w-full">
                {parentLink.label}
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      aria-hidden="true"
      className={`transition-transform duration-[var(--sbs-motion-fast)] ease-[var(--sbs-ease-standard)] ${open ? "rotate-180" : ""}`}
    >
      <path d="M3 4.5 6 7.5 9 4.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Burger({ open }: { open: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d={open ? "M5 5l10 10" : "M3 6h14"}
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        className="transition-[d] duration-[var(--sbs-motion-fast)]"
      />
      <path d="M3 10h14" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" opacity={open ? 0 : 1} />
      <path
        d={open ? "M15 5L5 15" : "M3 14h14"}
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}
