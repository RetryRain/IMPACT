import { NextResponse } from "next/server";
import { getStoryById } from "@/lib/queries";
import { scopeToPath, storyPath } from "@/lib/scope";
import { absoluteUrl } from "@/lib/site";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(_request: Request, context: RouteContext) {
  const { id } = await context.params;
  const story = await getStoryById(id);

  if (!story) {
    return NextResponse.redirect(absoluteUrl("/"), 302);
  }

  const scopePath = scopeToPath(story.scope);
  if (!scopePath || !story.slug) {
    return NextResponse.redirect(absoluteUrl("/"), 302);
  }

  const canonical = absoluteUrl(storyPath(scopePath, story.slug));
  return NextResponse.redirect(canonical, 301);
}
