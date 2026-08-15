import { NextResponse } from "next/server";
import { getFeedStories } from "@/lib/queries";
import { scopeToPath, storyPath } from "@/lib/scope";
import { isScopePath } from "@/lib/scope";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const scopeParam = searchParams.get("scope");
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const limit = Math.min(
    50,
    Math.max(1, Number(searchParams.get("limit") ?? "20") || 20),
  );

  const scope =
    scopeParam && isScopePath(scopeParam) ? scopeParam : undefined;
  const feed = await getFeedStories(scope, page);

  const stories = feed.stories.slice(0, limit).map((story) => {
    const scopePath = scopeToPath(story.scope);
    return {
      id: story.id,
      title: story.title,
      slug: story.slug,
      summary: story.summary,
      scope: story.scope,
      priority: story.priority,
      publishedAt: story.publishedAt?.toISOString() ?? null,
      sources: story.sources,
      url: scopePath ? storyPath(scopePath, story.slug) : null,
    };
  });

  return NextResponse.json({
    stories,
    page: feed.page,
    totalPages: feed.totalPages,
    total: feed.total,
  });
}
