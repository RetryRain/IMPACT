import { NextRequest, NextResponse } from "next/server";
import { getCanonicalStoryIds } from "@/lib/queries";
import { isScopePath, type ScopePath } from "@/lib/scope";

export async function GET(request: NextRequest) {
  const scopeParam = request.nextUrl.searchParams.get("scope");
  let scopePath: ScopePath | undefined;
  if (scopeParam) {
    if (!isScopePath(scopeParam)) {
      return NextResponse.json({ error: "Invalid scope" }, { status: 400 });
    }
    scopePath = scopeParam;
  }

  const ids = await getCanonicalStoryIds(scopePath);
  return NextResponse.json(
    { ids },
    {
      headers: {
        "Cache-Control": "s-maxage=60, stale-while-revalidate",
      },
    },
  );
}
