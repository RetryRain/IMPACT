import { NextResponse } from "next/server";
import { getLatestStories } from "@/lib/queries";
import { scopeToPath, storyPath } from "@/lib/scope";
import { absoluteUrl, SITE_DESCRIPTION, SITE_NAME } from "@/lib/site";

export async function GET() {
  const stories = await getLatestStories(50);
  const items = stories
    .map((story) => {
      const scope = scopeToPath(story.scope);
      if (!scope || !story.slug) return null;
      const link = absoluteUrl(storyPath(scope, story.slug));
      const pubDate = story.publishedAt?.toUTCString() ?? "";
      const description = story.summary ?? "";
      return `
    <item>
      <title>${escapeXml(story.title)}</title>
      <link>${link}</link>
      <guid isPermaLink="true">${link}</guid>
      <pubDate>${pubDate}</pubDate>
      <description>${escapeXml(description)}</description>
    </item>`;
    })
    .filter(Boolean)
    .join("");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>${escapeXml(SITE_NAME)}</title>
    <link>${absoluteUrl("/")}</link>
    <description>${escapeXml(SITE_DESCRIPTION)}</description>
    <language>en-in</language>
    ${items}
  </channel>
</rss>`;

  return new NextResponse(xml, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
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
