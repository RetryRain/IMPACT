import Link from "next/link";
import { FeedbackButton } from "./FeedbackButton";
import { SITE_NAME } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="border-t border-border mt-16">
      <div className="mx-auto max-w-5xl px-4 py-10 text-sm text-muted font-sans space-y-4">
        <p className="max-w-article leading-relaxed">
          <strong className="text-ink">{SITE_NAME}</strong> — no noise, no
          duplicates, no bullshit. Just what affects <em>you</em> in Tamil Nadu.
        </p>
        <div className="flex flex-wrap gap-4 items-center">
          <Link
            href="/about"
            className="hover:text-accent underline-offset-2 hover:underline"
          >
            About
          </Link>
          <FeedbackButton />
        </div>
        <p className="text-xs">
          Install this site from your browser menu to use {SITE_NAME} as an app.
        </p>
      </div>
    </footer>
  );
}
