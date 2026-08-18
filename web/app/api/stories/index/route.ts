import { NextResponse } from "next/server";
import { getStorySearchIndex } from "@/lib/queries";

export async function GET() {
  const stories = await getStorySearchIndex();
  return NextResponse.json(
    { stories },
    {
      headers: {
        "Cache-Control": "s-maxage=120, stale-while-revalidate",
      },
    },
  );
}
