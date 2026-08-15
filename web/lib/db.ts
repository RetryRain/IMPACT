import { neon } from "@neondatabase/serverless";
import { drizzle } from "drizzle-orm/neon-http";
import * as schema from "./schema";

function normalizeDatabaseUrl(raw: string): string {
  return raw.replace(/^postgresql\+psycopg:/, "postgres:");
}

export function isDatabaseConfigured(): boolean {
  return !!(process.env.SYNTHESIS_DATABASE_URL ?? process.env.DATABASE_URL);
}

export function getDatabaseUrl(): string {
  const url =
    process.env.SYNTHESIS_DATABASE_URL ?? process.env.DATABASE_URL;
  if (!url) {
    throw new Error(
      "SYNTHESIS_DATABASE_URL or DATABASE_URL is required for the web app",
    );
  }
  return normalizeDatabaseUrl(url);
}

export function getDb() {
  const sql = neon(getDatabaseUrl());
  return drizzle(sql, { schema });
}
