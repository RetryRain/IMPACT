import Image from "next/image";
import Link from "next/link";
import type { Story } from "@/lib/schema";
import { scopeToPath, storyPath } from "@/lib/scope";
import { formatRelativeIst, truncate } from "@/lib/format";

export function FeedCard({ story }: { story: Story }) {
  const scopePath = scopeToPath(story.scope);
  const href = scopePath
    ? storyPath(scopePath, story.slug)
    : `/s/${story.id}`;
  const sourceCount = story.sources?.length ?? 0;

  return (
    <article className="group border-b border-border py-6 first:pt-0">
      <Link href={href} className="block gap-4 sm:grid sm:grid-cols-[1fr_200px]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-xs font-sans text-muted mb-2">
            <span className="rounded-full bg-border/80 px-2 py-0.5 text-ink">
              {story.scope}
            </span>
            <time dateTime={story.publishedAt?.toISOString() ?? undefined}>
              {formatRelativeIst(story.publishedAt)}
            </time>
            {sourceCount > 0 && (
              <span>{sourceCount} source{sourceCount !== 1 ? "s" : ""}</span>
            )}
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
        <div className="mt-4 sm:mt-0 relative aspect-[16/10] rounded-lg overflow-hidden bg-gradient-to-br from-border to-paper">
          {story.image ? (
            <Image
              src={story.image}
              alt=""
              fill
              className="object-cover"
              sizes="200px"
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-xs text-muted font-sans px-4 text-center">
              Bytez
            </div>
          )}
        </div>
      </Link>
    </article>
  );
}
