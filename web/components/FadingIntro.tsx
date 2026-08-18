"use client";

import { useEffect, useState, type ReactNode } from "react";

const FADE_MS = 6000;

type FadingIntroProps = {
  children: ReactNode;
  className?: string;
};

export function FadingIntro({ children, className = "" }: FadingIntroProps) {
  const [phase, setPhase] = useState<"visible" | "fading" | "hidden">(
    "visible",
  );

  useEffect(() => {
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    if (reducedMotion) {
      const hideTimer = window.setTimeout(() => setPhase("hidden"), FADE_MS);
      return () => window.clearTimeout(hideTimer);
    }

    const fadeTimer = window.setTimeout(() => setPhase("fading"), FADE_MS);
    const hideTimer = window.setTimeout(
      () => setPhase("hidden"),
      FADE_MS + 700,
    );

    return () => {
      window.clearTimeout(fadeTimer);
      window.clearTimeout(hideTimer);
    };
  }, []);

  if (phase === "hidden") return null;

  return (
    <p
      className={`font-sans text-muted leading-relaxed transition-opacity duration-700 ease-out ${
        phase === "fading" ? "opacity-0" : "opacity-100"
      } ${className}`}
    >
      {children}
    </p>
  );
}
