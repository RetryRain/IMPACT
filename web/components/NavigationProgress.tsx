"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

export function NavigationProgress() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [active, setActive] = useState(false);
  const [width, setWidth] = useState(30);
  const prevRoute = useRef("");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const routeKey = `${pathname}?${searchParams.toString()}`;

  const startProgress = useCallback(() => {
    setActive(true);
    setWidth(30);
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(() => {
      setWidth((w) => (w >= 80 ? 80 : w + 4));
    }, 120);
  }, []);

  const completeProgress = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setWidth(100);
    const t = setTimeout(() => {
      setActive(false);
      setWidth(30);
    }, 200);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (prevRoute.current && prevRoute.current !== routeKey) {
      completeProgress();
    }
    prevRoute.current = routeKey;
  }, [routeKey, completeProgress]);

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      const target = event.target as Element | null;
      const anchor = target?.closest("a");
      if (!anchor) return;
      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#")) return;
      if (anchor.target === "_blank") return;
      if (href.startsWith("http") && !href.startsWith(window.location.origin)) {
        return;
      }
      startProgress();
    };

    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, [startProgress]);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  if (!active) return null;

  return (
    <div
      className="absolute left-0 top-0 h-0.5 bg-accent transition-[width] duration-150 ease-out z-[60]"
      style={{ width: `${width}%` }}
      aria-hidden="true"
    />
  );
}
