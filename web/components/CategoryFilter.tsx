"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  CATEGORY_LABELS,
  CATEGORY_SLUGS,
  type CategorySlug,
  readSavedCategoryFilter,
  saveCategoryFilter,
} from "@/lib/categories";

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

function triggerLabel(selected: CategorySlug[]): string {
  if (selected.length === 0) return "All topics";
  if (selected.length === 1) return CATEGORY_LABELS[selected[0]];
  return `${selected.length} topics`;
}

export function CategoryFilter() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<CategorySlug[]>([]);
  const [toast, setToast] = useState<string | null>(null);
  const appliedSavedRef = useRef(false);
  const toastTimer = useRef<number | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  const applyCategories = useCallback(
    (categories: CategorySlug[]) => {
      const params = new URLSearchParams(searchParams.toString());
      params.delete("category");
      params.delete("page");
      for (const slug of categories) {
        params.append("category", slug);
      }
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  useEffect(() => {
    const fromUrl = searchParams.getAll("category").filter((value): value is CategorySlug =>
      (CATEGORY_SLUGS as readonly string[]).includes(value),
    );
    if (fromUrl.length > 0) {
      setSelected(fromUrl);
      appliedSavedRef.current = true;
      return;
    }
    const saved = readSavedCategoryFilter();
    setSelected(saved);
    if (saved.length > 0 && !appliedSavedRef.current) {
      appliedSavedRef.current = true;
      applyCategories(saved);
    }
  }, [searchParams, applyCategories]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  useEffect(() => {
    return () => {
      if (toastTimer.current) window.clearTimeout(toastTimer.current);
    };
  }, []);

  const showToast = (message: string) => {
    setToast(null);
    window.requestAnimationFrame(() => setToast(message));
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 2400);
  };

  const toggle = (slug: CategorySlug) => {
    const next = selected.includes(slug)
      ? selected.filter((item) => item !== slug)
      : [...selected, slug];
    setSelected(next);
    applyCategories(next);
  };

  const handleSave = () => {
    saveCategoryFilter(selected);
    showToast(
      selected.length === 0
        ? "Showing all topics"
        : "Category preferences saved",
    );
    setOpen(false);
  };

  const handleClear = () => {
    setSelected([]);
    applyCategories([]);
    saveCategoryFilter([]);
    showToast("Filters cleared");
  };

  return (
    <>
      <div ref={rootRef} className="relative inline-flex max-w-full items-center">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="inline-flex max-w-full items-center rounded-md border border-border/80 bg-paper py-1.5 pl-3 pr-7 text-xs font-sans text-muted transition-colors hover:border-border hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent/25"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-label="Select categories"
        >
          {triggerLabel(selected)}
        </button>
        <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-muted/45" />

        {open && (
          <div className="absolute left-0 top-full z-50 mt-1 w-56 overflow-hidden rounded-md border border-border bg-paper shadow-lg">
            <div className="flex items-center justify-between gap-2 border-b border-border px-2 py-1.5">
              <button
                type="button"
                onClick={handleSave}
                className="rounded px-2 py-1 text-xs font-sans text-accent hover:bg-accent-soft"
              >
                Save
              </button>
              <button
                type="button"
                onClick={handleClear}
                className="rounded px-2 py-1 text-xs font-sans text-muted hover:bg-border/60 hover:text-ink"
              >
                Clear
              </button>
            </div>
            <ul className="max-h-64 overflow-y-auto py-1" role="listbox" aria-multiselectable="true">
              {CATEGORY_SLUGS.map((slug) => {
                const checked = selected.includes(slug);
                return (
                  <li key={slug}>
                    <label className="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-xs font-sans text-ink hover:bg-border/40">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggle(slug)}
                        className="h-3.5 w-3.5 rounded border-border text-accent accent-accent"
                      />
                      {CATEGORY_LABELS[slug]}
                    </label>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>
      {toast && (
        <div
          role="status"
          className="pointer-events-none fixed bottom-24 md:bottom-8 left-1/2 z-[90] rounded-full bg-ink px-4 py-2 text-xs font-sans text-paper shadow-lg animate-toast"
        >
          {toast}
        </div>
      )}
    </>
  );
}
