import { and, count, desc, eq, isNull, sql } from "drizzle-orm";
import { getDb } from "./db";
import {
  storyRedirects,
  synthesizedStories,
  type Story,
  type StoryRedirect,
} from "./schema";
import { pathToScopeLabel, scopeToPath, type ScopePath } from "./scope";

export const FEED_PAGE_SIZE = 20;

export type FeedResult = {
  stories: Story[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

function feedOrder() {
  return [
    desc(synthesizedStories.priority),
    desc(synthesizedStories.publishedAt),
  ];
}

function feedConditions(scopePath?: ScopePath) {
  const conditions = [isNull(synthesizedStories.canonicalStoryId)];
  if (scopePath) {
    const label = pathToScopeLabel(scopePath);
    if (label) {
      conditions.push(eq(synthesizedStories.scope, label));
    }
  }
  return and(...conditions);
}

export async function getFeedStories(
  scopePath?: ScopePath,
  page = 1,
): Promise<FeedResult> {
  const db = getDb();
  const pageSize = FEED_PAGE_SIZE;
  const offset = (page - 1) * pageSize;
  const whereClause = feedConditions(scopePath);

  const [stories, totalRow] = await Promise.all([
    db
      .select()
      .from(synthesizedStories)
      .where(whereClause)
      .orderBy(...feedOrder())
      .limit(pageSize)
      .offset(offset),
    db
      .select({ count: count() })
      .from(synthesizedStories)
      .where(whereClause),
  ]);

  const total = Number(totalRow[0]?.count ?? 0);
  return {
    stories,
    total,
    page,
    pageSize,
    totalPages: Math.max(1, Math.ceil(total / pageSize)),
  };
}

export async function getStoryBySlug(
  scopePath: ScopePath,
  slug: string,
): Promise<Story | null> {
  const label = pathToScopeLabel(scopePath);
  if (!label) return null;

  const db = getDb();
  const rows = await db
    .select()
    .from(synthesizedStories)
    .where(
      and(eq(synthesizedStories.slug, slug), eq(synthesizedStories.scope, label)),
    )
    .limit(1);

  return rows[0] ?? null;
}

export async function getStoryById(id: string): Promise<Story | null> {
  const db = getDb();
  const rows = await db
    .select()
    .from(synthesizedStories)
    .where(eq(synthesizedStories.id, id))
    .limit(1);
  return rows[0] ?? null;
}

export async function getStoryRedirectBySlug(
  scopePath: ScopePath,
  slug: string,
): Promise<StoryRedirect | null> {
  const label = pathToScopeLabel(scopePath);
  if (!label) return null;

  const db = getDb();
  const rows = await db
    .select()
    .from(storyRedirects)
    .where(
      and(eq(storyRedirects.slug, slug), eq(storyRedirects.scope, label)),
    )
    .limit(1);
  return rows[0] ?? null;
}

export async function getStoryRedirectByStoryId(
  id: string,
): Promise<StoryRedirect | null> {
  const db = getDb();
  const rows = await db
    .select()
    .from(storyRedirects)
    .where(eq(storyRedirects.storyId, id))
    .limit(1);
  return rows[0] ?? null;
}

export async function getRelatedStories(
  story: Story,
  limit = 4,
): Promise<Story[]> {
  const db = getDb();
  return db
    .select()
    .from(synthesizedStories)
    .where(
      and(
        isNull(synthesizedStories.canonicalStoryId),
        eq(synthesizedStories.scope, story.scope ?? ""),
        sql`${synthesizedStories.id} != ${story.id}`,
      ),
    )
    .orderBy(...feedOrder())
    .limit(limit);
}

export async function getLatestStories(limit = 50): Promise<Story[]> {
  const db = getDb();
  return db
    .select()
    .from(synthesizedStories)
    .where(isNull(synthesizedStories.canonicalStoryId))
    .orderBy(...feedOrder())
    .limit(limit);
}

export async function getAllStoryPaths(limit = 200): Promise<
  Array<{ scope: ScopePath; slug: string }>
> {
  const stories = await getLatestStories(limit);
  const paths: Array<{ scope: ScopePath; slug: string }> = [];
  for (const story of stories) {
    const scope = scopeToPath(story.scope);
    if (scope && story.slug) {
      paths.push({ scope, slug: story.slug });
    }
  }
  return paths;
}

export async function getRecentNewsStories(withinHours = 48): Promise<Story[]> {
  const db = getDb();
  const cutoff = new Date(Date.now() - withinHours * 60 * 60 * 1000);
  return db
    .select()
    .from(synthesizedStories)
    .where(
      and(
        isNull(synthesizedStories.canonicalStoryId),
        sql`${synthesizedStories.publishedAt} >= ${cutoff}`,
      ),
    )
    .orderBy(...feedOrder())
    .limit(500);
}

export async function getCanonicalStoryIds(scopePath?: ScopePath): Promise<string[]> {
  const db = getDb();
  const conditions = [isNull(synthesizedStories.canonicalStoryId)];
  if (scopePath) {
    const label = pathToScopeLabel(scopePath);
    if (label) {
      conditions.push(eq(synthesizedStories.scope, label));
    }
  }
  const rows = await db
    .select({ id: synthesizedStories.id })
    .from(synthesizedStories)
    .where(and(...conditions));
  return rows.map((row) => row.id);
}

export type StorySearchIndexItem = {
  id: string;
  title: string;
  summary: string | null;
  slug: string;
  scope: string | null;
  publishedAt: string | null;
};

export async function getStorySearchIndex(): Promise<StorySearchIndexItem[]> {
  const db = getDb();
  const rows = await db
    .select({
      id: synthesizedStories.id,
      title: synthesizedStories.title,
      summary: synthesizedStories.summary,
      slug: synthesizedStories.slug,
      scope: synthesizedStories.scope,
      publishedAt: synthesizedStories.publishedAt,
    })
    .from(synthesizedStories)
    .where(isNull(synthesizedStories.canonicalStoryId))
    .orderBy(...feedOrder());

  return rows.map((row) => ({
    id: row.id,
    title: row.title,
    summary: row.summary,
    slug: row.slug,
    scope: row.scope,
    publishedAt: row.publishedAt?.toISOString() ?? null,
  }));
}

export async function resolveCanonicalStory(story: Story): Promise<Story> {
  if (!story.canonicalStoryId) return story;
  const canonical = await getStoryById(story.canonicalStoryId);
  return canonical ?? story;
}
