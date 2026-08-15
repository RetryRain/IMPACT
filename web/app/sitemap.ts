import type { MetadataRoute } from "next";
import { getLatestStories } from "@/lib/queries";
import { scopeToPath, storyPath, SCOPE_PATHS } from "@/lib/scope";
import { absoluteUrl } from "@/lib/site";
import { isDatabaseConfigured } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: absoluteUrl("/"), lastModified: now, changeFrequency: "hourly", priority: 1 },
    ...SCOPE_PATHS.map((scope) => ({
      url: absoluteUrl(`/${scope}`),
      lastModified: now,
      changeFrequency: "hourly" as const,
      priority: 0.9,
    })),
  ];

  if (!isDatabaseConfigured()) {
    return staticRoutes;
  }

  try {
    const stories = await getLatestStories(500);
    const articleRoutes: MetadataRoute.Sitemap = stories
    .map((story) => {
      const scope = scopeToPath(story.scope);
      if (!scope || !story.slug) return null;
      return {
        url: absoluteUrl(storyPath(scope, story.slug)),
        lastModified: story.synthesizedAt ?? story.publishedAt ?? now,
        changeFrequency: "weekly" as const,
        priority: 0.8,
      };
    })
    .filter((entry): entry is NonNullable<typeof entry> => entry !== null);

    return [...staticRoutes, ...articleRoutes];
  } catch {
    return staticRoutes;
  }
}
