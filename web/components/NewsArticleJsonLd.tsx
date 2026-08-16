import type { Story } from "@/lib/schema";
import { storyKeywords } from "@/lib/keywords";
import { absoluteUrl, SITE_NAME } from "@/lib/site";
import { scopeToPath, storyPath } from "@/lib/scope";

type NewsArticleJsonLdProps = {
  story: Story;
};

export function NewsArticleJsonLd({ story }: NewsArticleJsonLdProps) {
  const scopePath = scopeToPath(story.scope);
  const url =
    scopePath
      ? absoluteUrl(storyPath(scopePath, story.slug))
      : absoluteUrl("/");
  const keywords = storyKeywords(story.tags);

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: story.title,
    description: story.summary ?? undefined,
    keywords,
    image: story.image ? [story.image] : undefined,
    datePublished: story.publishedAt?.toISOString(),
    dateModified: story.synthesizedAt.toISOString(),
    inLanguage: story.language ?? "en",
    isBasedOn: story.sourceUrls?.map((sourceUrl) => ({
      "@type": "CreativeWork",
      url: sourceUrl,
    })),
    mainEntityOfPage: url,
    publisher: {
      "@type": "Organization",
      name: SITE_NAME,
      url: absoluteUrl("/"),
    },
    url,
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
