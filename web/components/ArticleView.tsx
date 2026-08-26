"use client";

import { useEffect, useState } from "react";
import { ArticlePager } from "@/components/ArticlePager";
import { ArticlePane, type ArticleNeighbor, type ArticlePaneData } from "@/components/ArticlePane";
import {
  findQueueIndex,
  getReadingQueue,
  type ReadingQueueItem,
} from "@/lib/reading-queue";
import type { ResolvedPublisher } from "@/lib/publishers";
import { storyPath, type ScopePath } from "@/lib/scope";

type ArticleViewProps = {
  story: ArticlePaneData;
  scopePath: ScopePath;
  slug: string;
  publishers: ResolvedPublisher[];
  pageUrl: string;
  publishedAt: Date;
};

function nextFromQueue(
  items: ReadingQueueItem[],
  scopePath: ScopePath,
  slug: string,
): ArticleNeighbor | null {
  const idx = findQueueIndex(items, scopePath, slug);
  const next = idx >= 0 ? items[idx + 1] : items[0];
  if (!next || (next.scope === scopePath && next.slug === slug)) return null;
  return {
    href: storyPath(next.scope as ScopePath, next.slug),
    title: next.title ?? "Next story",
  };
}

export function ArticleView({
  story,
  scopePath,
  slug,
  publishers,
  pageUrl,
  publishedAt,
}: ArticleViewProps) {
  const paneStory: ArticlePaneData = {
    ...story,
    publishers,
    pageUrl,
    publishedAt,
  };
  const [nextStory, setNextStory] = useState<ArticleNeighbor | null>(null);

  useEffect(() => {
    const items = getReadingQueue();
    if (items.length > 0) {
      setNextStory(nextFromQueue(items, scopePath, slug));
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
      setNextStory(nextFromQueue(data.items, scopePath, slug));
    })();
    return () => {
      cancelled = true;
    };
  }, [scopePath, slug]);

  return (
    <>
      <div className="hidden md:block">
        <ArticlePane
          story={paneStory}
          scopePath={scopePath}
          nextStory={nextStory}
        />
      </div>
      <div className="md:hidden">
        <ArticlePager
          initialStory={paneStory}
          scopePath={scopePath}
          slug={slug}
        />
      </div>
    </>
  );
}
