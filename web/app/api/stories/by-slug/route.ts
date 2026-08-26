import { NextRequest, NextResponse } from "next/server";
import { getStoryBySlug } from "@/lib/queries";
import { resolveStoryPublishers } from "@/lib/publishers";
import { isScopePath, type ScopePath } from "@/lib/scope";

export async function GET(request: NextRequest) {
  const scope = request.nextUrl.searchParams.get("scope");
  const slug = request.nextUrl.searchParams.get("slug");

  if (!scope || !slug || !isScopePath(scope)) {
    return NextResponse.json({ error: "Invalid scope or slug" }, { status: 400 });
  }

  const story = await getStoryBySlug(scope as ScopePath, slug);
  if (!story) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const sourceUrls = story.sourceUrls ?? [];
  const publishers = resolveStoryPublishers(story.sources ?? [], sourceUrls);

  return NextResponse.json(
    {
      story: {
        id: story.id,
        slug: story.slug,
        scope: story.scope,
        category: story.category,
        title: story.title,
        summary: story.summary,
        body: story.body,
        image: story.image,
        tags: story.tags,
        publishedAt: story.publishedAt?.toISOString() ?? null,
        createdAt: story.createdAt.toISOString(),
        synthesizedAt: story.synthesizedAt.toISOString(),
        publishers,
      },
    },
    {
      headers: {
        "Cache-Control": "s-maxage=60, stale-while-revalidate",
      },
    },
  );
}
