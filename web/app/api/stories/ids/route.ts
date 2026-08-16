import { NextResponse } from "next/server";
import { getCanonicalStoryIds } from "@/lib/queries";

export async function GET() {
  const ids = await getCanonicalStoryIds();
  return NextResponse.json(
    { ids },
    {
      headers: {
        "Cache-Control": "s-maxage=60, stale-while-revalidate",
      },
    },
  );
}
