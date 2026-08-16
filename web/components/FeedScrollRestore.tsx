"use client";

import { useLayoutEffect, type ReactNode } from "react";

export function FeedScrollRestore({ children }: { children: ReactNode }) {
  useLayoutEffect(() => {
    if ("scrollRestoration" in history) {
      history.scrollRestoration = "manual";
    }

    const key = `bytez:scroll:${window.location.pathname}${window.location.search}`;
    const saved = sessionStorage.getItem(key);
    if (!saved) return;

    const y = Number.parseInt(saved, 10);
    if (Number.isNaN(y)) return;

    window.scrollTo({ top: y, left: 0, behavior: "instant" });
  }, []);

  return children;
}
