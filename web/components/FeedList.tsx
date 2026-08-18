"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { FeedCard } from "./FeedCard";
import { FeedScrollRestore } from "./FeedScrollRestore";
import type { Story } from "@/lib/schema";
import { consumeFeedReturnFromArticle } from "@/lib/feed-order";
import { getReadStoryIds } from "@/lib/visited-store";
import { isScopePath } from "@/lib/scope";

function partitionStories(stories: Story[], readIds: Set<string>): Story[] {
  const unread: Story[] = [];
  const read: Story[] = [];
  for (const story of stories) {
    if (readIds.has(story.id)) {
      read.push(story);
    } else {
      unread.push(story);
    }
  }
  return [...unread, ...read];
}

function scopeFromPathname(pathname: string): string | undefined {
  const segment = pathname.split("/").filter(Boolean)[0];
  if (segment && isScopePath(segment)) return segment;
  if (pathname === "/") return undefined;
  return undefined;
}

export function FeedList({ stories }: { stories: Story[] }) {
  const pathname = usePathname();
  const [readIds, setReadIds] = useState<Set<string>>(new Set());
  const [displayStories, setDisplayStories] = useState<Story[]>(stories);

  const refreshReadIds = useCallback(async () => {
    const ids = await getReadStoryIds();
    setReadIds(new Set(ids));
  }, []);

  useEffect(() => {
    let active = true;

    const applyOrder = async () => {
      const ids = await getReadStoryIds();
      if (!active) return;

      setReadIds(new Set(ids));

      const returnedFromArticle = consumeFeedReturnFromArticle();
      if (returnedFromArticle) {
        setDisplayStories(stories);
        return;
      }

      setDisplayStories(partitionStories(stories, new Set(ids)));
    };

    applyOrder();
    return () => {
      active = false;
    };
  }, [pathname, stories]);

  useEffect(() => {
    const onStoryRead = () => refreshReadIds();
    window.addEventListener("tnforme:story-read", onStoryRead);
    return () => window.removeEventListener("tnforme:story-read", onStoryRead);
  }, [refreshReadIds]);

  if (stories.length === 0) {
    return (
      <p className="font-sans text-muted py-12 text-center">
        No stories yet. Check back later.
      </p>
    );
  }

  return (
    <>
      <FeedScrollRestore>
        <div>
          {displayStories.map((story) => (
            <FeedCard key={story.id} story={story} />
          ))}
        </div>
      </FeedScrollRestore>
      <ReadProgressBar scope={scopeFromPathname(pathname)} readIds={readIds} />
    </>
  );
}

function ReadProgressBar({
  scope,
  readIds,
}: {
  scope?: string;
  readIds: Set<string>;
}) {
  const [allIds, setAllIds] = useState<string[]>([]);

  useEffect(() => {
    const params = scope ? `?scope=${encodeURIComponent(scope)}` : "";
    fetch(`/api/stories/ids${params}`)
      .then((response) => response.json())
      .then((data: { ids?: string[] }) => setAllIds(data.ids ?? []))
      .catch(() => setAllIds([]));
  }, [scope]);

  const readCount = allIds.filter((id) => readIds.has(id)).length;
  const total = allIds.length;
  const progress =
    total > 0 ? Math.min(100, Math.round((readCount / total) * 100)) : 0;

  if (total === 0) return null;

  return (
    <div
      className="pointer-events-none fixed inset-x-0 z-[80] md:bottom-0 bottom-[calc(4.5rem+env(safe-area-inset-bottom,0px))]"
      aria-hidden="true"
    >
      <div className="h-0.5 bg-border/40">
        <div
          className="h-full bg-accent/70 transition-[width] duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
