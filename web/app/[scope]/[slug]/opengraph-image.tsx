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
    <svg width="40" height="40" viewBox="0 0 500 500">
      <defs>
        <linearGradient id="og-stream" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#059669" />
          <stop offset="50%" stopColor="#10B981" />
          <stop offset="100%" stopColor="#34D399" />
        </linearGradient>
        <linearGradient id="og-stream-inner" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#065F46" />
          <stop offset="100%" stopColor="#047857" />
        </linearGradient>
      </defs>
      <path
        d="M 250, 70 C 290, 130 360, 210 360, 290 C 360, 370 310, 420 250, 420 C 190, 420 140, 370 140, 290 C 140, 230 180, 160 220, 120 C 210, 160 210, 190 225, 220 C 240, 250 265, 270 270, 300 C 275, 330 260, 355 240, 365 C 290, 360 320, 320 315, 270 C 310, 220 270, 160 250, 70 Z"
        fill="url(#og-stream)"
      />
      <path
        d="M 245, 160 C 270, 210 300, 250 295, 300 C 290, 340 265, 365 235, 370 C 260, 350 270, 320 260, 290 C 250, 260 225, 240 220, 210 C 215, 185 230, 170 245, 160 Z"
        fill="url(#og-stream-inner)"
      />
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
