import { neon } from "@neondatabase/serverless";
import { drizzle } from "drizzle-orm/neon-http";
import * as schema from "./feedback-schema";

function normalizeDatabaseUrl(raw: string): string {
  return raw.replace(/^postgresql\+psycopg:/, "postgres:");
}

export function isFeedbackDatabaseConfigured(): boolean {
  return !!process.env.FEEDBACK_DATABASE_URL;
}

export function getFeedbackDatabaseUrl(): string {
  const url = process.env.FEEDBACK_DATABASE_URL;
  if (!url) {
    throw new Error("FEEDBACK_DATABASE_URL is required for feedback");
  }
  return normalizeDatabaseUrl(url);
}

export function getFeedbackDb() {
  const sql = neon(getFeedbackDatabaseUrl());
  return drizzle(sql, { schema });
}
