export const SITE_NAME = "TNDecaf";

export const SITE_TAGLINE = "Quality news without the bait";

export const SITE_DESCRIPTION =
  "TNDecaf is a free news briefing for Tamil Nadu readers. Short original stories on Tamil Nadu, India, and the world. No clickbait, no ads, no account.";

export function getSiteUrl(): string {
  const url = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  return url.replace(/\/$/, "");
}

export function absoluteUrl(path: string): string {
  const base = getSiteUrl();
  return path.startsWith("http") ? path : `${base}${path.startsWith("/") ? path : `/${path}`}`;
}
