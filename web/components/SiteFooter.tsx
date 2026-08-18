import Link from "next/link";
import { FeedbackButton } from "./FeedbackButton";
import { SITE_NAME } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="border-t border-border mt-16 pb-tab-bar">
      <div className="mx-auto max-w-5xl px-4 py-10 text-sm text-muted font-sans space-y-4">
        <p className="max-w-article leading-relaxed">
          <strong className="text-accent">{SITE_NAME}</strong> publishes Tamil
          Nadu news without engagement bait. Free, no ads, no account.
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
