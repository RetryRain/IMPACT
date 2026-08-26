"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArticlePane, type ArticlePaneData } from "@/components/ArticlePane";
import { MarkStoryRead } from "@/components/MarkStoryRead";
import {
  findQueueIndex,
  getReadingQueue,
  type ReadingQueueItem,
} from "@/lib/reading-queue";
import { storyPath, type ScopePath } from "@/lib/scope";
import { markStoryRead } from "@/lib/visited-store";

const PRELOAD_RADIUS = 2;
const storyCache = new Map<string, CachedStory>();

type CachedStory = ArticlePaneData & { scopePath: ScopePath };

type ArticlePagerProps = {
  initialStory: ArticlePaneData;
  scopePath: ScopePath;
  slug: string;
};

function queueKey(item: Pick<ReadingQueueItem, "scope" | "slug">) {
  return `${item.scope}/${item.slug}`;
}

function toPaneData(
  raw: {
    id: string;
    slug: string;
    scope: string | null;
    category: string | null;
    title: string;
    summary: string | null;
    body: string | null;
    image: string | null;
    tags: string[] | null;
    publishedAt: string | null;
    publishers: ArticlePaneData["publishers"];
  },
  scopePath: ScopePath,
): CachedStory {
  return {
    id: raw.id,
    slug: raw.slug,
    scope: raw.scope,
    category: raw.category,
    title: raw.title,
    summary: raw.summary,
    body: raw.body,
    image: raw.image,
    tags: raw.tags,
    publishedAt: raw.publishedAt,
    publishers: raw.publishers,
    scopePath,
    pageUrl:
      typeof window !== "undefined"
        ? `${window.location.origin}${storyPath(scopePath, raw.slug)}`
        : storyPath(scopePath, raw.slug),
  };
}

function neighborFromQueue(
  item: ReadingQueueItem | undefined,
): { href: string; title: string } | null {
  if (!item) return null;
  const cached = storyCache.get(queueKey(item));
  return {
    href: storyPath(item.scope as ScopePath, item.slug),
    title: cached?.title ?? item.title ?? "Next story",
  };
}

export function ArticlePager({ initialStory, scopePath, slug }: ArticlePagerProps) {
  const trackRef = useRef<HTMLDivElement>(null);
  const surfaceRef = useRef<HTMLDivElement>(null);
  const [queue, setQueue] = useState<ReadingQueueItem[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [viewportWidth, setViewportWidth] = useState(0);
  const [peeking, setPeeking] = useState(false);
  const [, setCacheTick] = useState(0);
  const draggingRef = useRef(false);
  const trackingHorizontal = useRef(false);
  const startXRef = useRef(0);
  const startYRef = useRef(0);
  const offsetRef = useRef(0);
  const indexRef = useRef(0);
  const widthRef = useRef(0);
  const queueRef = useRef<ReadingQueueItem[]>([]);

  useEffect(() => {
    const initial: CachedStory = {
      ...initialStory,
      scopePath,
      pageUrl:
        typeof window !== "undefined"
          ? `${window.location.origin}${storyPath(scopePath, slug)}`
          : storyPath(scopePath, slug),
    };
    storyCache.set(queueKey({ scope: scopePath, slug }), initial);
  }, [initialStory, scopePath, slug]);

  useEffect(() => {
    const items = getReadingQueue();
    if (items.length > 0) {
      setQueue(items);
      const idx = findQueueIndex(items, scopePath, slug);
      setActiveIndex(idx >= 0 ? idx : 0);
      return;
    }

    let cancelled = false;
    (async () => {
      const res = await fetch(
        `/api/stories/queue?scope=${encodeURIComponent(scopePath)}`,
      );
      if (!res.ok || cancelled) return;
      const data = (await res.json()) as { items: ReadingQueueItem[] };
      if (cancelled) return;
      setQueue(data.items);
      const idx = findQueueIndex(data.items, scopePath, slug);
      setActiveIndex(idx >= 0 ? idx : 0);
    })();

    return () => {
      cancelled = true;
    };
  }, [scopePath, slug]);

  useEffect(() => {
    markStoryRead(initialStory.id, slug);
  }, [initialStory.id, slug]);

  useEffect(() => {
    const update = () => setViewportWidth(window.innerWidth);
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  const fetchStory = useCallback(async (item: ReadingQueueItem) => {
    const key = queueKey(item);
    if (storyCache.has(key)) return storyCache.get(key)!;

    const res = await fetch(
      `/api/stories/by-slug?scope=${encodeURIComponent(item.scope)}&slug=${encodeURIComponent(item.slug)}`,
    );
    if (!res.ok) return null;
    const data = (await res.json()) as { story: Parameters<typeof toPaneData>[0] };
    const pane = toPaneData(data.story, item.scope as ScopePath);
    storyCache.set(key, pane);
    setCacheTick((n) => n + 1);
    return pane;
  }, []);

  const preloadNeighbors = useCallback(
    async (center: number, items: ReadingQueueItem[]) => {
      const tasks: Promise<unknown>[] = [];
      for (let delta = -PRELOAD_RADIUS; delta <= PRELOAD_RADIUS; delta++) {
        const idx = center + delta;
        if (idx >= 0 && idx < items.length) {
          tasks.push(fetchStory(items[idx]));
        }
      }
      await Promise.all(tasks);
    },
    [fetchStory],
  );

  useEffect(() => {
    if (queue.length === 0) return;
    preloadNeighbors(activeIndex, queue);
  }, [queue, activeIndex, preloadNeighbors]);

  useEffect(() => {
    indexRef.current = activeIndex;
    widthRef.current = viewportWidth;
    queueRef.current = queue;
  }, [activeIndex, viewportWidth, queue]);

  const commitIndex = useCallback((index: number) => {
    const items = queueRef.current;
    const item = items[index];
    if (!item) return;
    setActiveIndex(index);
    const path = storyPath(item.scope as ScopePath, item.slug);
    window.history.replaceState(window.history.state, "", path);
    const pane = storyCache.get(queueKey(item));
    if (pane) markStoryRead(pane.id, pane.slug);
    preloadNeighbors(index, items);
  }, [preloadNeighbors]);

  const snappingRef = useRef(false);

  const setTrackX = (x: number, animate: boolean) => {
    const el = trackRef.current;
    if (!el) return;
    el.style.transition = animate
      ? "transform 420ms cubic-bezier(0.22, 1, 0.36, 1)"
      : "none";
    el.style.transform = `translate3d(${x}px, 0, 0)`;
  };

  const snapTo = useCallback(
    (index: number) => {
      const width = widthRef.current;
      const clamped = Math.max(0, Math.min(index, queueRef.current.length - 1));
      offsetRef.current = 0;
      snappingRef.current = true;
      setTrackX(-clamped * width, true);
      if (clamped !== indexRef.current) {
        commitIndex(clamped);
      }
      window.setTimeout(() => {
        snappingRef.current = false;
        setPeeking(false);
      }, 430);
    },
    [commitIndex],
  );

  useEffect(() => {
    if (!trackRef.current || viewportWidth <= 0) return;
    if (snappingRef.current || draggingRef.current) return;
    setTrackX(-activeIndex * viewportWidth + offsetRef.current, false);
  }, [activeIndex, viewportWidth]);

  useEffect(() => {
    const surface = surfaceRef.current;
    if (!surface) return;

    const handleStart = (e: TouchEvent) => {
      if (queueRef.current.length <= 1) return;
      const touch = e.touches[0];
      startXRef.current = touch.clientX;
      startYRef.current = touch.clientY;
      draggingRef.current = true;
      trackingHorizontal.current = false;
      setTrackX(-indexRef.current * widthRef.current, false);
    };

    const handleMove = (e: TouchEvent) => {
      if (!draggingRef.current || queueRef.current.length <= 1) return;
      const touch = e.touches[0];
      const dx = touch.clientX - startXRef.current;
      const dy = touch.clientY - startYRef.current;
      const index = indexRef.current;
      const width = widthRef.current;
      const length = queueRef.current.length;

      if (!trackingHorizontal.current) {
        if (Math.abs(dx) < 10 && Math.abs(dy) < 10) return;
        if (Math.abs(dy) >= Math.abs(dx)) {
          draggingRef.current = false;
          return;
        }
        trackingHorizontal.current = true;
        setPeeking(true);
      }

      e.preventDefault();
      const atStart = index === 0 && dx > 0;
      const atEnd = index === length - 1 && dx < 0;
      const resisted = atStart || atEnd ? dx * 0.28 : dx;
      offsetRef.current = resisted;
      setTrackX(-index * width + resisted, false);
    };

    const handleEnd = () => {
      if (!draggingRef.current) return;
      const wasHorizontal = trackingHorizontal.current;
      draggingRef.current = false;
      trackingHorizontal.current = false;
      if (!wasHorizontal) {
        setPeeking(false);
        return;
      }
      const width = widthRef.current;
      const index = indexRef.current;
      const length = queueRef.current.length;
      const threshold = Math.max(56, width * 0.18);
      if (offsetRef.current < -threshold && index < length - 1) {
        snapTo(index + 1);
      } else if (offsetRef.current > threshold && index > 0) {
        snapTo(index - 1);
      } else {
        snapTo(index);
      }
    };

    surface.addEventListener("touchstart", handleStart, { passive: true });
    surface.addEventListener("touchmove", handleMove, { passive: false });
    surface.addEventListener("touchend", handleEnd);
    surface.addEventListener("touchcancel", handleEnd);
    return () => {
      surface.removeEventListener("touchstart", handleStart);
      surface.removeEventListener("touchmove", handleMove);
      surface.removeEventListener("touchend", handleEnd);
      surface.removeEventListener("touchcancel", handleEnd);
    };
  }, [snapTo, queue.length, viewportWidth]);

  const current = queue[activeIndex];
  const currentStory =
    (current && storyCache.get(queueKey(current))) ||
    ({ ...initialStory, scopePath } as CachedStory);
  const nextStory = neighborFromQueue(queue[activeIndex + 1]);

  if (viewportWidth === 0) {
    return (
      <>
        <MarkStoryRead id={initialStory.id} slug={slug} />
        <ArticlePane
          story={initialStory}
          scopePath={scopePath}
          nextStory={nextStory}
        />
      </>
    );
  }

  if (queue.length <= 1) {
    return (
      <>
        <MarkStoryRead id={currentStory.id} slug={currentStory.slug} />
        <ArticlePane
          story={currentStory}
          scopePath={scopePath}
          nextStory={nextStory}
        />
      </>
    );
  }

  const start = Math.max(0, activeIndex - PRELOAD_RADIUS);
  const end = Math.min(queue.length - 1, activeIndex + PRELOAD_RADIUS);

  return (
    <div className="md:hidden relative -mx-4 h-[calc(100dvh-7.5rem)] overflow-hidden">
      <div ref={surfaceRef} className="h-full overflow-hidden">
        <div
          ref={trackRef}
          className="flex h-full will-change-transform"
          style={{
            width: viewportWidth * queue.length,
            transform: `translate3d(${-activeIndex * viewportWidth}px, 0, 0)`,
          }}
        >
          {queue.map((item, index) => {
            const cached = storyCache.get(queueKey(item));
            const inWindow = index >= start && index <= end;
            const showBorder = peeking && index !== activeIndex;
            return (
              <div
                key={queueKey(item)}
                className={`h-full shrink-0 ${showBorder ? "border-x border-border" : "border-x border-transparent"}`}
                style={{ width: viewportWidth }}
              >
                {inWindow && cached ? (
                  <ArticlePane
                    story={cached}
                    scopePath={item.scope as ScopePath}
                    nextStory={neighborFromQueue(queue[index + 1])}
                    contained
                  />
                ) : (
                  <div className="h-[50vh]" />
                )}
              </div>
            );
          })}
        </div>
      </div>
      <MarkStoryRead id={currentStory.id} slug={currentStory.slug} />
    </div>
  );
}
