"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { markFeedReturnFromArticle } from "@/lib/feed-order";
import { isStoryRead } from "@/lib/visited-store";

type FeedCardLinkProps = {
  href: string;
  storyId: string;
  children: ReactNode;
};

function saveFeedScroll() {
  const key = `bytez:scroll:${window.location.pathname}${window.location.search}`;
  sessionStorage.setItem(key, String(window.scrollY));
}

export function FeedCardLink({ href, storyId, children }: FeedCardLinkProps) {
  const [read, setRead] = useState(false);

  useEffect(() => {
    let active = true;
    isStoryRead(storyId).then((value) => {
      if (active) setRead(value);
    });
    const onStoryRead = () => {
      isStoryRead(storyId).then((value) => {
        if (active) setRead(value);
      });
    };
    window.addEventListener("tnforme:story-read", onStoryRead);
    return () => {
      active = false;
      window.removeEventListener("tnforme:story-read", onStoryRead);
    };
  }, [storyId]);

  return (
    <Link
      href={href}
      onClick={() => {
        saveFeedScroll();
        markFeedReturnFromArticle();
      }}
      className={`block gap-4 sm:grid sm:grid-cols-[1fr_200px] ${
        read ? "[&_h2]:text-visited" : ""
      }`}
    >
      {children}
    </Link>
  );
}
