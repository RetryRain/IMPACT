/**
 * One-off publish DB migration runner (migration 003 slug).
 * Usage: node scripts/apply-publish-migration.mjs
 */
import { neon } from "@neondatabase/serverless";
import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

function loadEnv() {
  const envPath = resolve(__dirname, "../.env");
  try {
    const raw = readFileSync(envPath, "utf8");
    for (const line of raw.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eq = trimmed.indexOf("=");
      if (eq === -1) continue;
      const key = trimmed.slice(0, eq).trim();
      const value = trimmed.slice(eq + 1).trim();
      if (!process.env[key]) process.env[key] = value;
    }
  } catch {
  }
}

loadEnv();

const rawUrl =
  process.env.SYNTHESIS_DATABASE_URL ?? process.env.DATABASE_URL;
if (!rawUrl) {
  console.error("SYNTHESIS_DATABASE_URL is required in web/.env");
  process.exit(1);
}

const databaseUrl = rawUrl.replace(/^postgresql\+psycopg:/, "postgres:");
const sql = neon(databaseUrl);

async function columnExists() {
  const rows = await sql`
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'synthesized_stories'
      AND column_name = 'slug'
  `;
  return rows.length > 0;
}

async function getAlembicVersion() {
  try {
    const rows = await sql`SELECT version_num FROM alembic_version LIMIT 1`;
    return rows[0]?.version_num ?? null;
  } catch {
    return null;
  }
}

async function main() {
  const version = await getAlembicVersion();
  console.log(`Current alembic_version: ${version ?? "(none)"}`);

  if (await columnExists()) {
    console.log("slug column already exists — nothing to do.");
    if (version !== "003") {
      await sql`
        INSERT INTO alembic_version (version_num)
        VALUES ('003')
        ON CONFLICT (version_num) DO UPDATE SET version_num = '003'
      `.catch(async () => {
        await sql`UPDATE alembic_version SET version_num = '003'`;
      });
      console.log("Stamped alembic_version to 003");
    }
    return;
  }

  console.log("Applying migration 003 (slug)...");

  await sql`ALTER TABLE synthesized_stories ADD COLUMN slug VARCHAR(256)`;

  await sql`
    CREATE UNIQUE INDEX ix_synthesized_stories_slug
    ON synthesized_stories (slug)
  `;

  await sql`
    UPDATE synthesized_stories
    SET slug = (
      trim(both '-' from regexp_replace(
        lower(regexp_replace(title, '[^\\w\\s-]', '', 'g')),
        '[\\s_-]+', '-', 'g'
      ))
      || '-' || left(replace(id::text, '-', ''), 6)
    )
    WHERE slug IS NULL
  `;

  await sql`ALTER TABLE synthesized_stories ALTER COLUMN slug SET NOT NULL`;

  if (version === null) {
    await sql`CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)`;
    await sql`INSERT INTO alembic_version (version_num) VALUES ('003')`;
  } else {
    await sql`UPDATE alembic_version SET version_num = '003'`;
  }

  console.log("Migration 003 applied successfully.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
