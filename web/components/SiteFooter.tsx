import Link from "next/link";
import { SITE_NAME, absoluteUrl } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="border-t border-border mt-16">
      <div className="mx-auto max-w-5xl px-4 py-10 text-sm text-muted font-sans space-y-4">
        <p className="max-w-article leading-relaxed">
          <strong className="text-ink">{SITE_NAME}</strong> publishes events that
          matter to people in Tamil Nadu — not everything in the news, only what
          could affect your community, work, money, or government.
        </p>
        <div className="flex flex-wrap gap-4">
          <Link href="/rss.xml" className="hover:text-accent underline-offset-2 hover:underline">
            RSS
          </Link>
          <a
            href={absoluteUrl("/sitemap.xml")}
            className="hover:text-accent underline-offset-2 hover:underline"
          >
            Sitemap
          </a>
        </div>
        <p className="text-xs">
          Install this site from your browser menu to use {SITE_NAME} as an app.
        </p>
      </div>
    </footer>
  );
}
