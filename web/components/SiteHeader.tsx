import Link from "next/link";
import { SCOPE_LABELS, SCOPE_PATHS } from "@/lib/scope";
import { SITE_NAME } from "@/lib/site";

export function SiteHeader() {
  return (
    <header className="border-b border-border bg-paper/95 backdrop-blur sticky top-0 z-50">
      <div className="mx-auto max-w-5xl px-4 py-4 flex items-center justify-between gap-4">
        <Link href="/" className="font-serif text-2xl font-bold text-ink tracking-tight">
          {SITE_NAME}
        </Link>
        <nav className="flex flex-wrap gap-1 sm:gap-3 text-sm font-sans">
          {SCOPE_PATHS.map((path) => (
            <Link
              key={path}
              href={`/${path}`}
              className="px-3 py-1.5 rounded-full text-muted hover:text-ink hover:bg-border/60 transition-colors"
            >
              {SCOPE_LABELS[path]}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
