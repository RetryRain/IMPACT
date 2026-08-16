import {
  pgTable,
  text,
  timestamp,
  uuid,
} from "drizzle-orm/pg-core";

export const feedback = pgTable("feedback", {
  id: uuid("id").primaryKey().defaultRandom(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  message: text("message").notNull(),
  email: text("email"),
  pageUrl: text("page_url"),
  userAgent: text("user_agent"),
});

export type FeedbackRow = typeof feedback.$inferSelect;
