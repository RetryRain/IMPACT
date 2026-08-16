import { NextResponse } from "next/server";
import { getRecentNewsStories } from "@/lib/queries";
import { scopeToPath, storyPath } from "@/lib/scope";
import { absoluteUrl, SITE_NAME } from "@/lib/site";

export async function GET() {
  const stories = await getRecentNewsStories(48);
  const now = new Date();

  const urls = stories
    .map((story) => {
      const scope = scopeToPath(story.scope);
      if (!scope || !story.slug || !story.publishedAt) return null;
      const loc = absoluteUrl(storyPath(scope, story.slug));
      const pubDate = story.publishedAt.toISOString();
      const title = escapeXml(story.title);
      return `
  <url>
    <loc>${loc}</loc>
    <news:news>
      <news:publication>
        <news:name>${escapeXml(SITE_NAME)}</news:name>
        <news:language>en</news:language>
      </news:publication>
      <news:publication_date>${pubDate}</news:publication_date>
      <news:title>${title}</news:title>
    </news:news>
  </url>`;
    })
    .filter(Boolean)
    .join("");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
  ${urls}
</urlset>`;

  return new NextResponse(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "s-maxage=300, stale-while-revalidate",
    },
  });
}

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
