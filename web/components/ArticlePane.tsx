"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import Image from "next/image";
import Link from "next/link";
import { ArticleBackButton } from "@/components/ArticleBackButton";
import { ArticleBody } from "@/components/ArticleBody";
import { FeedbackButton } from "@/components/FeedbackButton";
import { PublisherLogos } from "@/components/PublisherLogos";
import { ShareStoryButton } from "@/components/ShareStoryButton";
import { StoryPublishedDate } from "@/components/StoryPublishedDate";
import { categoryChipClass, categoryLabel } from "@/lib/categories";
import type { ResolvedPublisher } from "@/lib/publishers";
import { scopeChipClass, type ScopePath } from "@/lib/scope";

export type ArticleNeighbor = {
  href: string;
  title: string;
};

export type ArticlePaneData = {
  id: string;
  slug: string;
  scope: string | null;
  category: string | null;
  title: string;
  summary: string | null;
  body: string | null;
  image: string | null;
  tags: string[] | null;
  publishedAt: Date | string | null;
  pageUrl: string;
  publishers: ResolvedPublisher[];
};

type ArticlePaneProps = {
  story: ArticlePaneData;
  scopePath: ScopePath;
  nextStory?: ArticleNeighbor | null;
  /** When true, article is its own scroll container (mobile pager). */
  contained?: boolean;
};

function truncateTitle(title: string, max = 52): string {
  if (title.length <= max) return title;
  return `${title.slice(0, max - 1).trimEnd()}…`;
}

function SwipeNextHint({
  nextStory,
  storyId,
  scrollRoot,
}: {
  nextStory: ArticleNeighbor;
  storyId: string;
  scrollRoot?: HTMLElement | null;
}) {
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [token, setToken] = useState(0);
  const armedRef = useRef(true);

  useEffect(() => {
    armedRef.current = true;
    setVisible(false);
  }, [storyId, nextStory.href]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && armedRef.current) {
          armedRef.current = false;
          setToken((n) => n + 1);
          setVisible(true);
        } else if (!entry.isIntersecting) {
          armedRef.current = true;
        }
      },
      {
        root: scrollRoot ?? null,
        rootMargin: scrollRoot ? "0px 0px -8px 0px" : "0px 0px -72px 0px",
        threshold: 0,
      },
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [storyId, nextStory.href, scrollRoot]);

  return (
    <>
      <div ref={sentinelRef} className="h-px w-full shrink-0" aria-hidden="true" />
      {visible &&
        typeof document !== "undefined" &&
        createPortal(
          <div
            key={token}
            className="md:hidden fixed inset-x-4 bottom-[calc(4.75rem+env(safe-area-inset-bottom,0px))] z-[70] pointer-events-none"
            onAnimationEnd={() => setVisible(false)}
          >
            <div className="mx-auto max-w-article animate-next-hint rounded-lg border border-border bg-paper/95 px-3 py-2.5 shadow-md backdrop-blur-sm">
              <p className="font-sans text-sm text-accent leading-snug">
                <span className="font-medium">Next:</span>{" "}
                {truncateTitle(nextStory.title)}
              </p>
              <p className="mt-0.5 font-sans text-xs text-muted">
                Swipe left for the next story
              </p>
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}

export function ArticlePane({
  story,
  scopePath,
  nextStory,
  contained = false,
}: ArticlePaneProps) {
  const [scrollRoot, setScrollRoot] = useState<HTMLElement | null>(null);
  const publishedAt =
    story.publishedAt instanceof Date
      ? story.publishedAt
      : story.publishedAt
        ? new Date(story.publishedAt)
        : null;
  const category = categoryLabel(story.category);

  return (
    <article
      ref={(node) => {
        if (contained) setScrollRoot(node);
      }}
      className={`max-w-article mx-auto px-4 md:px-0 ${
        contained ? "h-full overflow-y-auto overscroll-y-contain" : ""
      }`}
    >
      <div className="mb-4 hidden md:block">
        <ArticleBackButton scopePath={scopePath} className="text-muted" />
      </div>

      <header className="mb-6">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-sans text-muted mb-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className={scopeChipClass(story.scope)}>{story.scope}</span>
            {category && story.category && (
              <span className={categoryChipClass(story.category)}>
                {category}
              </span>
            )}
            {publishedAt && <StoryPublishedDate date={publishedAt} />}
          </div>
          <ShareStoryButton title={story.title} url={story.pageUrl} />
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl font-bold text-ink leading-tight">
          {story.title}
        </h1>
        {story.summary && (
          <p className="mt-3 font-sans text-lg text-muted leading-relaxed">
            {story.summary}
          </p>
        )}
      </header>

      {story.image && (
        <div className="relative aspect-[16/9] rounded-lg overflow-hidden mb-6 bg-border">
          <Image
            src={story.image}
            alt=""
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 672px"
            priority
          />
        </div>
      )}

      {story.body && <ArticleBody body={story.body} />}

      {story.tags && story.tags.length > 0 && (
        <ul className="sr-only">
          {story.tags.map((tag) => (
            <li key={tag}>{tag}</li>
          ))}
        </ul>
      )}

      {nextStory && (
        <SwipeNextHint
          nextStory={nextStory}
          storyId={story.id}
          scrollRoot={contained ? scrollRoot : null}
        />
      )}

      <section className="mt-6 border-t border-border pt-3 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          {story.publishers.length > 0 && (
            <>
              <p className="text-xs font-sans uppercase tracking-wide text-muted shrink-0">
                From
              </p>
              <PublisherLogos
                publishers={story.publishers}
                linked
                className="justify-start"
              />
            </>
          )}
        </div>
        <FeedbackButton pageUrl={story.pageUrl} className="shrink-0 text-sm text-muted" />
      </section>

      <div className="mt-4 flex items-center justify-between gap-3 pb-tab-bar md:pb-8">
        <ArticleBackButton
          scopePath={scopePath}
          className="text-muted hover:text-ink"
        />
        {nextStory && (
          <Link
            href={nextStory.href}
            className="hidden md:inline-flex font-sans text-sm text-accent hover:underline"
          >
            Next article →
          </Link>
        )}
      </div>
    </article>
  );
}
