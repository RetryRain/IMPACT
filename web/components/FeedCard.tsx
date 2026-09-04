import Image from "next/image";
import type { Story } from "@/lib/schema";
import { scopeToPath, storyPath, scopeChipClass } from "@/lib/scope";
import { truncate } from "@/lib/format";
import { FeedCardLink } from "./FeedCardLink";
import { RelativeTime } from "./RelativeTime";
import { StreamMark } from "./StreamMark";
import { categoryChipClass, categoryLabel } from "@/lib/categories";

export function FeedCard({ story }: { story: Story }) {
  const scopePath = scopeToPath(story.scope);
  const href = scopePath
    ? storyPath(scopePath, story.slug)
    : `/s/${story.id}`;

  const category = categoryLabel(story.category);

  return (
    <article className="group border-b border-border py-6 first:pt-0">
      <FeedCardLink href={href} storyId={story.id}>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-xs font-sans text-muted mb-2">
            <span className={scopeChipClass(story.scope)}>
              {story.scope}
            </span>
            {category && story.category && (
              <span className={categoryChipClass(story.category)}>
                {category}
              </span>
            )}
            <RelativeTime date={story.publishedAt ?? story.createdAt} />
          </div>
          <h2 className="font-serif text-xl sm:text-2xl font-bold text-ink group-hover:text-accent transition-colors leading-snug">
            {story.title}
          </h2>
          {story.summary && (
            <p className="mt-2 font-sans text-muted leading-relaxed line-clamp-3">
              {truncate(story.summary, 220)}
            </p>
          )}
        </div>
        <div className="mt-4 sm:mt-0 relative aspect-[16/10] rounded-lg overflow-hidden bg-gradient-to-br from-accent-soft to-paper">
          {story.image ? (
            <Image
              src={story.image}
              alt=""
              fill
              className="object-cover"
              // Article images are immutable publisher URLs; bypass the Vercel
              // optimizer to avoid per-URL image-transformation usage spikes.
              unoptimized
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center px-4">
              <StreamMark
                className="h-12 w-12 opacity-50"
                idPrefix={`feed-${story.id}`}
              />
            </div>
          )}
        </div>
      </FeedCardLink>
    </article>
  );
}
