import Link from "next/link";
import { FeedbackButton } from "./FeedbackButton";
import { SITE_NAME } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="hidden md:block border-t border-border mt-16 pb-tab-bar">
      <div className="mx-auto max-w-5xl px-4 py-6 text-sm text-muted font-sans space-y-3">
        <p className="max-w-article leading-relaxed">
          <strong className="text-accent">{SITE_NAME}</strong> publishes quality
          news without engagement bait. Tamil Nadu, India, and the world. Free,
          no ads, no account.
        </p>
        <div className="flex flex-wrap gap-4 items-center">
          <Link
            href="/about"
            className="hover:text-accent underline-offset-2 hover:underline"
          >
            About
          </Link>
          <FeedbackButton />
          <Link
            href="/privacy"
            className="hover:text-accent underline-offset-2 hover:underline"
          >
            Privacy
          </Link>
          <Link
            href="/terms"
            className="hover:text-accent underline-offset-2 hover:underline"
          >
            Terms
          </Link>
        </div>
      </div>
    </footer>
  );
}
