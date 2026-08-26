"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Fuse from "fuse.js";
import { scopeToPath, storyPath } from "@/lib/scope";
import type { StorySearchIndexItem } from "@/lib/queries";

type SearchOverlayProps = {
  open: boolean;
  onClose: () => void;
};

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-3.5-3.5" strokeLinecap="round" />
    </svg>
  );
}

export function SearchTrigger({
  onClick,
  className,
}: {
  onClick: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={className}
      aria-label="Search articles"
    >
      <SearchIcon className="h-5 w-5" />
    </button>
  );
}

export function SearchOverlay({ open, onClose }: SearchOverlayProps) {
  const [query, setQuery] = useState("");
  const [stories, setStories] = useState<StorySearchIndexItem[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    fetch("/api/stories/index")
      .then((response) => response.json())
      .then((data: { stories?: StorySearchIndexItem[] }) => {
        setStories(data.stories ?? []);
      })
      .catch(() => setStories([]))
      .finally(() => setLoading(false));
    inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null;
      if (panelRef.current?.contains(target)) return;
      onClose();
    };

    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  const fuse = useMemo(
    () =>
      new Fuse(stories, {
        keys: [
          { name: "title", weight: 0.7 },
          { name: "summary", weight: 0.3 },
        ],
        threshold: 0.4,
        ignoreLocation: true,
      }),
    [stories],
  );

  const results = useMemo(() => {
    const trimmed = query.trim();
    if (!trimmed) return [];
    return fuse.search(trimmed).slice(0, 12);
  }, [fuse, query]);

  const handleResultClick = useCallback(() => {
    onClose();
  }, [onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100]">
      <button
        type="button"
        className="absolute inset-0 bg-ink/40 backdrop-blur-sm"
        aria-label="Close search"
        onClick={onClose}
      />
      <div ref={panelRef} className="relative mx-auto mt-16 max-w-xl px-4">
        <div className="rounded-2xl border border-border bg-paper shadow-xl overflow-hidden">
          <div className="flex items-center gap-3 border-b border-border px-4 py-3">
            <SearchIcon className="h-5 w-5 text-muted shrink-0" />
            <input
              ref={inputRef}
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search all articles…"
              className="w-full bg-transparent font-sans text-ink placeholder:text-muted outline-none"
              aria-label="Search articles"
            />
          </div>

          <div className="max-h-[min(60vh,28rem)] overflow-y-auto">
            {loading && (
              <p className="px-4 py-6 text-sm text-muted font-sans">Loading…</p>
            )}
            {!loading && query.trim() && results.length === 0 && (
              <p className="px-4 py-6 text-sm text-muted font-sans">
                No matches for &ldquo;{query.trim()}&rdquo;
              </p>
            )}
            {!loading &&
              results.map(({ item }) => {
                const scopePath = scopeToPath(item.scope);
                const href = scopePath
                  ? storyPath(scopePath, item.slug)
                  : `/s/${item.id}`;
                return (
                  <Link
                    key={item.id}
                    href={href}
                    onClick={handleResultClick}
                    className="block border-b border-border/60 px-4 py-3 hover:bg-accent-soft/40 transition-colors last:border-b-0"
                  >
                    <p className="font-serif text-base font-semibold text-ink leading-snug">
                      {item.title}
                    </p>
                    {item.summary && (
                      <p className="mt-1 text-sm text-muted line-clamp-2 font-sans">
                        {item.summary}
                      </p>
                    )}
                    {item.scope && (
                      <p className="mt-2 text-xs text-muted font-sans">
                        {item.scope}
                      </p>
                    )}
                  </Link>
                );
              })}
          </div>
        </div>
      </div>
    </div>
  );
}
