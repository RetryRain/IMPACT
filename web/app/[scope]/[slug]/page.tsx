import Image from "next/image";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ArticleBody } from "@/components/ArticleBody";
import { NewsArticleJsonLd } from "@/components/NewsArticleJsonLd";
import { RelatedStories } from "@/components/RelatedStories";
import { formatIstDate } from "@/lib/format";
import {
  getRelatedStories,
  getStoryBySlug,
} from "@/lib/queries";
import {
  isScopePath,
  storyPath,
  type ScopePath,
} from "@/lib/scope";
import { absoluteUrl } from "@/lib/site";

export const dynamic = "force-dynamic";
export const revalidate = 300;

type PageProps = {
  params: Promise<{ scope: string; slug: string }>;
};

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { scope, slug } = await params;
  if (!isScopePath(scope)) return { title: "Not found" };

  const story = await getStoryBySlug(scope as ScopePath, slug);
  if (!story) return { title: "Not found" };

  const url = absoluteUrl(storyPath(scope as ScopePath, slug));
  const description = story.summary ?? story.title;

  return {
    title: story.title,
    description,
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

  const story = await getStoryBySlug(scope as ScopePath, slug);
  if (!story) {
    notFound();
  }

  const related = await getRelatedStories(story);
  const sources = story.sources ?? [];
  const sourceUrls = story.sourceUrls ?? [];

  return (
    <>
      <NewsArticleJsonLd story={story} />
      <article className="max-w-article">
        <header className="mb-8">
          <div className="flex flex-wrap items-center gap-2 text-xs font-sans text-muted mb-4">
            <span className="rounded-full bg-border/80 px-2 py-0.5 text-ink">
              {story.scope}
            </span>
            {story.publishedAt && (
              <time dateTime={story.publishedAt.toISOString()}>
                {formatIstDate(story.publishedAt)} IST
              </time>
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
          {sources.length > 0 && (
            <p className="mt-4 font-sans text-sm text-muted">
              Synthesized from {sources.join(", ")}
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

        {sourceUrls.length > 0 && (
          <section className="mt-10 border-t border-border pt-6">
            <h2 className="font-serif text-lg font-bold mb-3">Sources</h2>
            <ul className="space-y-2 font-sans text-sm">
              {sourceUrls.map((url) => (
                <li key={url}>
                  <a
                    href={url}
                    rel="noopener noreferrer"
                    target="_blank"
                    className="text-accent hover:underline break-all"
                  >
                    {url}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        )}
      </article>

      <RelatedStories stories={related} />
    </>
  );
}
