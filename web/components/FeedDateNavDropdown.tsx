"use client";

import type { ChangeEvent } from "react";
import { FEED_SORT_LATEST_OPTION } from "@/lib/feed-sort";

type FeedDateOption = {
  value: string;
  label: string;
};

type FeedDateNavDropdownProps = {
  basePath: string;
  options: FeedDateOption[];
  value: string;
};

function ChevronDown({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 12 12"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <path
        d="M2.5 4.5 6 8l3.5-3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function FeedDateNavDropdown({
  basePath,
  options,
  value,
}: FeedDateNavDropdownProps) {
  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const next = event.target.value;
    if (next === FEED_SORT_LATEST_OPTION) {
      window.location.assign(`${basePath}?sort=latest`);
      return;
    }
    if (!next) {
      window.location.assign(basePath);
      return;
    }
    window.location.assign(`${basePath}?date=${next}`);
  };

  return (
    <nav className="mb-6" aria-label="Browse by date">
      <div className="relative inline-flex max-w-full items-center">
        <select
          value={value}
          onChange={handleChange}
          className="max-w-full appearance-none rounded-md border border-border/80 bg-paper py-1.5 pl-3 pr-7 text-xs font-sans text-muted transition-colors hover:border-border hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent/25 cursor-pointer"
          aria-label="Select date"
        >
          <option value={FEED_SORT_LATEST_OPTION}>Latest</option>
          <option value="">Today</option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-muted/45" />
      </div>
    </nav>
  );
}
