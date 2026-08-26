import { NextRequest, NextResponse } from "next/server";
import { parseFeedDateParam } from "@/lib/feed-dates";
import { parseFeedSortParam } from "@/lib/feed-sort";
import { getFeedStories } from "@/lib/queries";
import { isScopePath, scopeToPath, type ScopePath } from "@/lib/scope";
import { parseCategoryParams } from "@/lib/categories";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const scopeParam = params.get("scope");
  let scopePath: ScopePath | undefined;
  if (scopeParam) {
    if (!isScopePath(scopeParam)) {
      return NextResponse.json({ error: "Invalid scope" }, { status: 400 });
    }
    scopePath = scopeParam;
  }

  const date = parseFeedDateParam(params.get("date") ?? undefined);
  const sort = parseFeedSortParam(params.get("sort") ?? undefined);
  const categories = parseCategoryParams(params.getAll("category"));
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);

  const feed = await getFeedStories(scopePath, page, date, sort, categories);

  const items = feed.stories
    .map((story) => {
      const scope = scopeToPath(story.scope);
      if (!scope || !story.slug) return null;
      return { id: story.id, slug: story.slug, scope, title: story.title };
    })
    .filter(
      (item): item is {
        id: string;
        slug: string;
        scope: ScopePath;
        title: string;
      } => item !== null,
    );

  return NextResponse.json(
    { items, page: feed.page, totalPages: feed.totalPages },
    {
      headers: {
        "Cache-Control": "s-maxage=30, stale-while-revalidate",
      },
    },
  );
}
