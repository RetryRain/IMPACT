"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { FeedCard } from "./FeedCard";
import { FeedScrollRestore } from "./FeedScrollRestore";
import { useFeedReadProgress } from "./FeedReadProgress";
import type { Story } from "@/lib/schema";
import { consumeFeedReturnFromArticle } from "@/lib/feed-order";
import { getReadStoryIds } from "@/lib/visited-store";

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

export function FeedList({ stories }: { stories: Story[] }) {
  const pathname = usePathname();
  const { setReadIds } = useFeedReadProgress();
  const [displayStories, setDisplayStories] = useState<Story[]>(stories);

  const refreshReadIds = useCallback(async () => {
    const ids = await getReadStoryIds();
    setReadIds(new Set(ids));
  }, [setReadIds]);

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
  }, [pathname, stories, setReadIds]);

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
    <FeedScrollRestore>
      <div>
        {displayStories.map((story) => (
          <FeedCard key={story.id} story={story} />
        ))}
      </div>
    </FeedScrollRestore>
  );
}
