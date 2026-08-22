"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { usePathname } from "next/navigation";
import { isScopePath } from "@/lib/scope";

type FeedReadProgressContextValue = {
  readIds: Set<string>;
  setReadIds: (ids: Set<string>) => void;
};

const FeedReadProgressContext = createContext<FeedReadProgressContextValue | null>(
  null,
);

export function FeedReadProgressProvider({ children }: { children: ReactNode }) {
  const [readIds, setReadIdsState] = useState<Set<string>>(new Set());

  const setReadIds = useCallback((ids: Set<string>) => {
    setReadIdsState(ids);
  }, []);

  return (
    <FeedReadProgressContext.Provider value={{ readIds, setReadIds }}>
      {children}
    </FeedReadProgressContext.Provider>
  );
}

export function useFeedReadProgress() {
  const context = useContext(FeedReadProgressContext);
  if (!context) {
    throw new Error("useFeedReadProgress must be used within FeedReadProgressProvider");
  }
  return context;
}

function scopeFromPathname(pathname: string): string | undefined {
  const segment = pathname.split("/").filter(Boolean)[0];
  if (segment && isScopePath(segment)) return segment;
  return undefined;
}

function isFeedPath(pathname: string): boolean {
  if (pathname === "/") return true;
  const segment = pathname.split("/").filter(Boolean)[0];
  if (segment && isScopePath(segment)) {
    const rest = pathname.split("/").filter(Boolean).slice(1);
    return rest.length === 0;
  }
  return false;
}

export function FeedReadProgressStrip({ className }: { className?: string }) {
  const pathname = usePathname();
  const { readIds } = useFeedReadProgress();
  const [allIds, setAllIds] = useState<string[]>([]);
  const scope = scopeFromPathname(pathname);
  const onFeed = isFeedPath(pathname);

  useEffect(() => {
    if (!onFeed) {
      setAllIds([]);
      return;
    }
    const params = scope ? `?scope=${encodeURIComponent(scope)}` : "";
    fetch(`/api/stories/ids${params}`)
      .then((response) => response.json())
      .then((data: { ids?: string[] }) => setAllIds(data.ids ?? []))
      .catch(() => setAllIds([]));
  }, [onFeed, scope]);

  if (!onFeed || allIds.length === 0) return null;

  const readCount = allIds.filter((id) => readIds.has(id)).length;
  const progress = Math.min(100, Math.round((readCount / allIds.length) * 100));

  return (
    <div className={className} aria-hidden="true">
      <div className="h-0.5 bg-border/40">
        <div
          className="h-full bg-accent/70 transition-[width] duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

export function FeedReadProgressDesktopDock() {
  return (
    <FeedReadProgressStrip className="pointer-events-none fixed inset-x-0 bottom-0 z-[80] hidden md:block" />
  );
}
