"use client";

import Link from "next/link";
import { Suspense, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { SCOPE_LABELS, SCOPE_PATHS, scopeNavClass } from "@/lib/scope";
import { SITE_NAME } from "@/lib/site";
import { NavigationProgress } from "./NavigationProgress";
import { StreamMark } from "./StreamMark";

export function SiteHeader() {
  const pathname = usePathname();
  const homeActive = pathname === "/";
  const [collapsed, setCollapsed] = useState(false);
  const lastScrollY = useRef(0);

  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY;
      if (y < 12) {
        setCollapsed(false);
      } else if (y > lastScrollY.current + 6) {
        setCollapsed(true);
      } else if (y < lastScrollY.current - 6) {
        setCollapsed(false);
      }
      lastScrollY.current = y;
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`relative border-b border-border bg-paper/95 backdrop-blur sticky top-0 z-50 transition-transform duration-300 ease-out md:translate-y-0 ${
        collapsed ? "-translate-y-full" : "translate-y-0"
      }`}
    >
      <Suspense fallback={null}>
        <NavigationProgress />
      </Suspense>
      <div className="mx-auto max-w-5xl px-4 py-4 flex items-center justify-between gap-4">
        <Link
          href="/"
          className={`flex items-center gap-2 font-serif text-2xl font-bold text-accent tracking-tight border-b-2 pb-0.5 ${
            homeActive
              ? "border-accent"
              : "border-transparent hover:border-accent/40"
          }`}
        >
          <StreamMark className="h-8 w-8 shrink-0" idPrefix="header" />
          {SITE_NAME}
        </Link>
        <nav
          className="hidden md:flex flex-wrap gap-1 sm:gap-3 text-sm font-sans"
          aria-label="Scope"
        >
          {SCOPE_PATHS.map((path) => {
            const active =
              pathname === `/${path}` || pathname.startsWith(`/${path}/`);
            return (
              <Link
                key={path}
                href={`/${path}`}
                className={scopeNavClass(path, active)}
              >
                {SCOPE_LABELS[path]}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
