import type { NextConfig } from "next";
import withSerwistInit from "@serwist/next";

const withSerwist = withSerwistInit({
  swSrc: "app/sw.ts",
  swDest: "public/sw.js",
  disable: process.env.NODE_ENV === "development",
});

const nextConfig: NextConfig = {
  images: {
    // Next defaults this low because it cannot invalidate /_next/image.
    // Article images are immutable publisher URLs, so keep the optimizer
    // cache at the 1-year ceiling to avoid STALE re-transforms.
    minimumCacheTTL: 31536000,
    remotePatterns: [
      { protocol: "https", hostname: "**" },
      { protocol: "http", hostname: "**" },
    ],
  },
};

export default withSerwist(nextConfig);
