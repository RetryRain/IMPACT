import { ImageResponse } from "next/og";
import { getStoryBySlug } from "@/lib/queries";
import { isScopePath, type ScopePath } from "@/lib/scope";
import { SITE_NAME } from "@/lib/site";

export const runtime = "edge";
export const alt = `${SITE_NAME} article`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

type Props = {
  params: Promise<{ scope: string; slug: string }>;
};

export default async function OgImage({ params }: Props) {
  const { scope, slug } = await params;
  let title = SITE_NAME;

  if (isScopePath(scope)) {
    const story = await getStoryBySlug(scope as ScopePath, slug);
    if (story?.title) {
      title = story.title;
    }
  }

  const displayTitle =
    title.length > 120 ? `${title.slice(0, 117)}…` : title;

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          backgroundColor: "#faf9f7",
          padding: 64,
        }}
      >
        <div
          style={{
            fontSize: 48,
            fontWeight: 700,
            color: "#1a1a1a",
            lineHeight: 1.2,
            maxWidth: "90%",
          }}
        >
          {displayTitle}
        </div>
        <div
          style={{
            fontSize: 32,
            color: "#3d7a5c",
            fontWeight: 600,
          }}
        >
          {SITE_NAME}
        </div>
      </div>
    ),
    { ...size },
  );
}
