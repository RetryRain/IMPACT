import type { Story } from "@/lib/schema";
import { absoluteUrl } from "@/lib/site";
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

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: story.title,
    description: story.summary ?? undefined,
    image: story.image ? [story.image] : undefined,
    datePublished: story.publishedAt?.toISOString(),
    dateModified: story.synthesizedAt.toISOString(),
    inLanguage: story.language ?? "en",
    isBasedOn: story.sourceUrls?.map((url) => ({ "@type": "CreativeWork", url })),
    mainEntityOfPage: url,
    publisher: {
      "@type": "Organization",
      name: "Bytez",
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
