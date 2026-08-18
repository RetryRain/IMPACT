export const SITE_NAME = "TNDecaf";

export const SITE_TAGLINE = "Tamil Nadu news without the bait";

export const SITE_DESCRIPTION =
  "TNDecaf is a free Tamil Nadu news briefing. Short original stories on work, money, safety, and public life. No clickbait, no ads, no account.";

export function getSiteUrl(): string {
  const url = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  return url.replace(/\/$/, "");
}

export function absoluteUrl(path: string): string {
  const base = getSiteUrl();
  return path.startsWith("http") ? path : `${base}${path.startsWith("/") ? path : `/${path}`}`;
}
