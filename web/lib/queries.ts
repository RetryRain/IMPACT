import { and, count, desc, eq, sql } from "drizzle-orm";
import { getDb } from "./db";
import { synthesizedStories, type Story } from "./schema";
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

export async function getFeedStories(
  scopePath?: ScopePath,
  page = 1,
): Promise<FeedResult> {
  const db = getDb();
  const pageSize = FEED_PAGE_SIZE;
  const offset = (page - 1) * pageSize;

  const conditions = [];
  if (scopePath) {
    const label = pathToScopeLabel(scopePath);
    if (label) {
      conditions.push(eq(synthesizedStories.scope, label));
    }
  }

  const whereClause =
    conditions.length > 0 ? and(...conditions) : undefined;

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
    .where(sql`${synthesizedStories.publishedAt} >= ${cutoff}`)
    .orderBy(...feedOrder())
    .limit(500);
}
