import { pgTable, text, timestamp, integer, jsonb, uuid } from "drizzle-orm/pg-core";

export const synthesizedStories = pgTable("synthesized_stories", {
  id: uuid("id").primaryKey(),
  clusterId: uuid("cluster_id").notNull().unique(),
  title: text("title").notNull(),
  slug: text("slug").notNull().unique(),
  summary: text("summary"),
  body: text("body"),
  url: text("url").notNull(),
  source: text("source"),
  author: text("author"),
  image: text("image"),
  tags: jsonb("tags").$type<string[] | null>(),
  language: text("language"),
  scope: text("scope"),
  priority: integer("priority").notNull().default(0),
  publishedAt: timestamp("published_at", { withTimezone: true }),
  scrapedAt: timestamp("scraped_at", { withTimezone: true }),
  sourceUrls: jsonb("source_urls").$type<string[]>().notNull(),
  sources: jsonb("sources").$type<string[]>().notNull(),
  synthesizedAt: timestamp("synthesized_at", { withTimezone: true }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull(),
  canonicalStoryId: uuid("canonical_story_id"),
});

export const storyRedirects = pgTable("story_redirects", {
  storyId: uuid("story_id").primaryKey(),
  scope: text("scope").notNull(),
  slug: text("slug").notNull().unique(),
  sourceUrl: text("source_url").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull(),
});

export type Story = typeof synthesizedStories.$inferSelect;
export type StoryRedirect = typeof storyRedirects.$inferSelect;
