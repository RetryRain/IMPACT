import Image from "next/image";
import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { ArticleBackButton } from "@/components/ArticleBackButton";
import { ArticleBody } from "@/components/ArticleBody";
import { FeedbackButton } from "@/components/FeedbackButton";
import { PublisherLogos } from "@/components/PublisherLogos";
import { MarkStoryRead } from "@/components/MarkStoryRead";
import { NewsArticleJsonLd } from "@/components/NewsArticleJsonLd";
import { RelativeTime } from "@/components/RelativeTime";
import { storyKeywords } from "@/lib/keywords";
import { getStoryById, getStoryBySlug } from "@/lib/queries";
import {
  isScopePath,
  scopeToPath,
  storyPath,
  scopeChipClass,
  type ScopePath,
} from "@/lib/scope";
import { resolveStoryPublishers } from "@/lib/publishers";
import { absoluteUrl } from "@/lib/site";

export const dynamic = "force-dynamic";
export const revalidate = 300;

type PageProps = {
  params: Promise<{ scope: string; slug: string }>;
};

async function resolveArticleOrRedirect(scope: ScopePath, slug: string) {
  const story = await getStoryBySlug(scope, slug);
  if (!story) return null;
  if (!story.canonicalStoryId) return story;

  const canonical = await getStoryById(story.canonicalStoryId);
  if (!canonical?.scope) return story;

  const canonicalScope = scopeToPath(canonical.scope);
  if (!canonicalScope || !canonical.slug) return story;

  permanentRedirect(storyPath(canonicalScope, canonical.slug));
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { scope, slug } = await params;
  if (!isScopePath(scope)) return { title: "Not found" };

  const story = await resolveArticleOrRedirect(scope as ScopePath, slug);
  if (!story) return { title: "Not found" };

  const url = absoluteUrl(storyPath(scope as ScopePath, slug));
  const description = story.summary ?? story.title;
  const keywords = storyKeywords(story.tags);

  return {
    title: story.title,
    description,
    keywords,
    alternates: { canonical: url },
    openGraph: {
      type: "article",
      title: story.title,
      description,
      url,
      publishedTime: story.publishedAt?.toISOString(),
      modifiedTime: story.synthesizedAt.toISOString(),
      section: story.scope ?? undefined,
      images: story.image ? [{ url: story.image }] : undefined,
    },
    twitter: {
      card: story.image ? "summary_large_image" : "summary",
      title: story.title,
      description,
      images: story.image ? [story.image] : undefined,
    },
  };
}

export default async function ArticlePage({ params }: PageProps) {
  const { scope, slug } = await params;
  if (!isScopePath(scope)) {
    notFound();
  }

  const story = await resolveArticleOrRedirect(scope as ScopePath, slug);
  if (!story) {
    notFound();
  }

  const sourceUrls = story.sourceUrls ?? [];
  const publishers = resolveStoryPublishers(story.sources ?? [], sourceUrls);
  const pageUrl = absoluteUrl(storyPath(scope as ScopePath, slug));

  return (
    <>
      <NewsArticleJsonLd story={story} />
      <MarkStoryRead id={story.id} slug={story.slug} />
      <article className="max-w-article mx-auto">
        <div className="mb-6">
          <ArticleBackButton scopePath={scope} />
        </div>

        <header className="mb-8">
          <div className="flex flex-wrap items-center gap-2 text-xs font-sans text-muted mb-4">
            <span className={scopeChipClass(story.scope)}>
              {story.scope}
            </span>
            {story.publishedAt && (
              <RelativeTime date={story.publishedAt} />
            )}
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl font-bold text-ink leading-tight">
            {story.title}
          </h1>
          {story.summary && (
            <p className="mt-4 font-sans text-lg text-muted leading-relaxed">
              {story.summary}
            </p>
          )}
        </header>

        {story.image && (
          <div className="relative aspect-[16/9] rounded-lg overflow-hidden mb-8 bg-border">
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

        {publishers.length > 0 && (
          <section className="mt-10 border-t border-border pt-6">
            <h2 className="font-serif text-lg font-bold mb-4">Sources</h2>
            <PublisherLogos
              publishers={publishers}
              linked
              className="justify-start"
            />
          </section>
        )}

        <div className="mt-10 border-t border-border pt-6 flex flex-wrap items-center gap-4">
          <ArticleBackButton scopePath={scope} />
          <FeedbackButton pageUrl={pageUrl} />
        </div>
      </article>
    </>
  );
}
