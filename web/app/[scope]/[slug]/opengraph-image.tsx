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

function OgStreamMark() {
  return (
    <svg width="40" height="40" viewBox="0 0 320 320">
      <path
        d="M 140 20 C 60 20, 20 80, 20 160 C 20 240, 60 300, 140 300 C 150 300, 155 295, 155 285 L 155 35 C 155 25, 150 20, 140 20 Z"
        fill="#0F382C"
      />
      <path
        d="M 180 20 L 230 20 L 290 80 L 290 160 C 290 240, 250 300, 180 300 C 170 300, 165 295, 165 285 L 165 35 C 165 25, 170 20, 180 20 Z"
        fill="#12B76A"
      />
      <path d="M 230 20 L 230 80 L 290 80 Z" fill="#0F382C" opacity="0.3" />
      <rect x="50" y="120" width="70" height="16" rx="8" fill="#FFFFFF" />
      <rect x="50" y="152" width="55" height="14" rx="7" fill="#FFFFFF" opacity="0.9" />
      <rect x="50" y="180" width="40" height="12" rx="6" fill="#FFFFFF" opacity="0.7" />
    </svg>
  );
}

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
            display: "flex",
            alignItems: "center",
            gap: 12,
            fontSize: 32,
            color: "#3d7a5c",
            fontWeight: 600,
          }}
        >
          <OgStreamMark />
          {SITE_NAME}
        </div>
      </div>
    ),
    { ...size },
  );
}
