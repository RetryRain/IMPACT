import type { Metadata } from "next";
import { notFound, permanentRedirect, redirect } from "next/navigation";
import { ArticleView } from "@/components/ArticleView";
import { MarkStoryRead } from "@/components/MarkStoryRead";
import { NewsArticleJsonLd } from "@/components/NewsArticleJsonLd";
import { storyKeywords } from "@/lib/keywords";
import {
  getStoryById,
  getStoryBySlug,
  getStoryRedirectBySlug,
} from "@/lib/queries";
import {
  isScopePath,
  scopeToPath,
  storyPath,
  type ScopePath,
} from "@/lib/scope";
import { resolveStoryPublishers } from "@/lib/publishers";
import { absoluteUrl } from "@/lib/site";
import type { Story } from "@/lib/schema";

export const dynamic = "force-dynamic";
export const revalidate = 300;

type PageProps = {
  params: Promise<{ scope: string; slug: string }>;
};

async function resolveArticleOrRedirect(
  scope: ScopePath,
  slug: string,
): Promise<Story | null> {
  const story = await getStoryBySlug(scope, slug);
  if (!story) {
    const tombstone = await getStoryRedirectBySlug(scope, slug);
    if (tombstone?.sourceUrl) {
      redirect(tombstone.sourceUrl);
    }
    return null;
  }

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

  const story = await getStoryBySlug(scope as ScopePath, slug);
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
  const publishedAt = story.publishedAt ?? story.createdAt;

  return (
    <>
      <NewsArticleJsonLd story={story} />
      <MarkStoryRead id={story.id} slug={story.slug} />
      <ArticleView
        story={{
          id: story.id,
          slug: story.slug,
          scope: story.scope,
          category: story.category,
          title: story.title,
          summary: story.summary,
          body: story.body,
          image: story.image,
          tags: story.tags,
          publishedAt,
          pageUrl,
          publishers,
        }}
        scopePath={scope as ScopePath}
        slug={slug}
        publishers={publishers}
        pageUrl={pageUrl}
        publishedAt={publishedAt}
      />
    </>
  );
}
