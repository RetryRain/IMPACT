import { and, count, desc, eq, isNull, sql, type SQL } from "drizzle-orm";
import { getDb } from "./db";
import { IST_TIMEZONE } from "./feed-dates";
import type { FeedSort } from "./feed-sort";
import {
  storyRedirects,
  synthesizedStories,
  type Story,
  type StoryRedirect,
} from "./schema";
import { pathToScopeLabel, scopeToPath, type ScopePath } from "./scope";

export const FEED_PAGE_SIZE = 20;
export const FEED_DEFAULT_HOURS = 24;

export type FeedResult = {
  stories: Story[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

const effectiveAt = sql`COALESCE(${synthesizedStories.publishedAt}, ${synthesizedStories.createdAt})`;

function feedOrder(sort: FeedSort = "priority") {
  if (sort === "latest") {
    return [desc(effectiveAt)];
  }
  return [
    desc(synthesizedStories.priority),
    desc(synthesizedStories.publishedAt),
  ];
}

function scopeCondition(scopePath?: ScopePath): SQL | undefined {
  if (!scopePath) return undefined;
  const label = pathToScopeLabel(scopePath);
  if (!label) return undefined;
  return eq(synthesizedStories.scope, label);
}

function feedTimeCondition(date?: string | null): SQL {
  if (date) {
    return sql`(timezone(${IST_TIMEZONE}, ${effectiveAt}))::date = ${date}::date`;
  }
  return sql`${effectiveAt} >= NOW() - (${FEED_DEFAULT_HOURS} * INTERVAL '1 hour')`;
}

function feedConditions(scopePath?: ScopePath, date?: string | null) {
  const conditions: (SQL | undefined)[] = [
    isNull(synthesizedStories.canonicalStoryId),
    scopeCondition(scopePath),
    feedTimeCondition(date),
  ];
  return and(...conditions.filter(Boolean));
}

export async function getFeedStories(
  scopePath?: ScopePath,
  page = 1,
  date?: string | null,
  sort: FeedSort = "priority",
): Promise<FeedResult> {
  const db = getDb();
  const pageSize = FEED_PAGE_SIZE;
  const offset = (page - 1) * pageSize;
  const whereClause = feedConditions(scopePath, date);

  const [stories, totalRow] = await Promise.all([
    db
      .select()
      .from(synthesizedStories)
      .where(whereClause)
      .orderBy(...feedOrder(sort))
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

export async function getFeedStoryDates(scopePath?: ScopePath): Promise<string[]> {
  const db = getDb();
  const conditions: (SQL | undefined)[] = [
    isNull(synthesizedStories.canonicalStoryId),
    scopeCondition(scopePath),
  ];
  const whereClause = and(...conditions.filter(Boolean));

  const storyDateIst = sql`(timezone(${IST_TIMEZONE}, COALESCE(${synthesizedStories.publishedAt}, ${synthesizedStories.createdAt})))::date`;

  const rows = await db
    .selectDistinct({
      storyDate: storyDateIst.as("story_date"),
    })
    .from(synthesizedStories)
    .where(whereClause);

  return rows
    .map((row) => String(row.storyDate).slice(0, 10))
    .filter((date) => /^\d{4}-\d{2}-\d{2}$/.test(date))
    .sort((a, b) => b.localeCompare(a));
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
  const whereClause = feedConditions(scopePath, null);
  const rows = await db
    .select({ id: synthesizedStories.id })
    .from(synthesizedStories)
    .where(whereClause);
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
