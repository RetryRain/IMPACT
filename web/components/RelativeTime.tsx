"use client";

import { useEffect, useState } from "react";

function formatRelative(date: Date): string {
  const now = Date.now();
  const diffMs = now - date.getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

type RelativeTimeProps = {
  date: Date | string | null;
  className?: string;
};

export function RelativeTime({ date, className }: RelativeTimeProps) {
  const iso =
    date instanceof Date ? date.toISOString() : date ? String(date) : null;
  const parsed = iso ? new Date(iso) : null;
  const [label, setLabel] = useState(() =>
    parsed ? formatRelative(parsed) : "",
  );

  useEffect(() => {
    if (!parsed || !iso) return;
    setLabel(formatRelative(parsed));
    const interval = window.setInterval(() => {
      setLabel(formatRelative(parsed));
    }, 60000);
    return () => window.clearInterval(interval);
  }, [iso]);

  if (!parsed) return null;

  return (
    <time dateTime={parsed.toISOString()} className={className}>
      {label}
    </time>
  );
}
