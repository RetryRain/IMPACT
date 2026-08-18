"use client";

import { useEffect, useState } from "react";

const IST = "Asia/Kolkata";

function parseDate(date: Date | string | null): Date | null {
  if (!date) return null;
  if (date instanceof Date) return date;
  const parsed = new Date(String(date));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatCalendarIst(date: Date): string {
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: IST,
    day: "numeric",
    month: "short",
  }).format(date);
}

function formatRelative(date: Date): string | null {
  const diffMs = Date.now() - date.getTime();
  const hours = Math.floor(diffMs / 3600000);
  if (hours < 0) return null;
  if (hours < 1) {
    const minutes = Math.max(1, Math.floor(diffMs / 60000));
    return `${minutes}m ago`;
  }
  if (hours < 24) return `${hours}h ago`;
  return null;
}

type StoryPublishedDateProps = {
  date: Date | string | null;
  className?: string;
};

export function StoryPublishedDate({ date, className }: StoryPublishedDateProps) {
  const parsed = parseDate(date);
  const iso = parsed?.toISOString() ?? null;
  const [relative, setRelative] = useState(() =>
    parsed ? formatRelative(parsed) : null,
  );

  useEffect(() => {
    if (!parsed || !iso) return;
    setRelative(formatRelative(parsed));
    const interval = window.setInterval(() => {
      setRelative(formatRelative(parsed));
    }, 60000);
    return () => window.clearInterval(interval);
  }, [iso, parsed]);

  if (!parsed) return null;

  const calendar = formatCalendarIst(parsed);

  return (
    <time dateTime={parsed.toISOString()} className={className}>
      {relative ? `${calendar} · ${relative}` : calendar}
    </time>
  );
}
