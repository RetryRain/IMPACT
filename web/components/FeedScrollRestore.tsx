"use client";

import { useEffect, type ReactNode } from "react";

export function FeedScrollRestore({ children }: { children: ReactNode }) {
  useEffect(() => {
    if ("scrollRestoration" in history) {
      history.scrollRestoration = "manual";
    }

    const key = `bytez:scroll:${window.location.pathname}${window.location.search}`;
    const saved = sessionStorage.getItem(key);
    if (!saved) return;

    const y = Number.parseInt(saved, 10);
    if (Number.isNaN(y)) return;

    requestAnimationFrame(() => {
      window.setTimeout(() => {
        window.scrollTo(0, y);
      }, 50);
    });
  }, []);

  return children;
}
