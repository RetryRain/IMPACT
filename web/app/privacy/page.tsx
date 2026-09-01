import type { Metadata } from "next";
import Link from "next/link";
import { SITE_NAME, absoluteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "Privacy",
  description:
    "How TNDecaf handles your data. No accounts, no ad tracking, read history stays on your device.",
  alternates: { canonical: absoluteUrl("/privacy") },
};

export default function PrivacyPage() {
  return (
    <article className="mx-auto max-w-article font-sans text-muted leading-relaxed space-y-6">
      <h1 className="font-serif text-4xl font-bold text-ink tracking-tight">
        Privacy
      </h1>
      <p className="text-lg">
        {SITE_NAME} is built to respect your time and your privacy. This is a
        straight summary — not legal theater.
      </p>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-bold text-ink">No accounts</h2>
        <p>
          We don&apos;t ask you to sign up, log in, or hand over an email to
          read the feed. There is no profile and no server-side history of what
          you&apos;ve opened.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-bold text-ink">
          Read history on your device
        </h2>
        <p>
          If you open a story, we may mark it as read in{" "}
          <strong className="text-ink">IndexedDB</strong> in your browser so the
          feed can show what you&apos;ve already seen. That data stays on your
          device. We don&apos;t sync it to our servers because we don&apos;t
          have a database of readers.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-bold text-ink">
          Category preferences
        </h2>
        <p>
          If you save category filters, that choice is stored in{" "}
          <strong className="text-ink">localStorage</strong> in your browser so
          the feed can remember your preferences. It never leaves your device
          and is not sent to our servers.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-bold text-ink">
          No analytics or ad tracking
        </h2>
        <p>
          We don&apos;t run third-party analytics, ad pixels, or behavioral
          tracking on {SITE_NAME}. No cookie banner because we&apos;re not
          trying to follow you around the web.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-bold text-ink">Feedback</h2>
        <p>
          If you send feedback, you choose what to share — usually an email or a
          note through our feedback flow. We use it only to respond or improve
          the product.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-bold text-ink">Sources</h2>
        <p>
          Stories cite facts from public reporting by established publishers. We
          don&apos;t collect your data when you follow those outbound links —
          you&apos;re leaving {SITE_NAME} and their policies apply.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-bold text-ink">Questions</h2>
        <p>
          Use <strong className="text-ink">Feedback</strong> in the site footer,
          or read more on{" "}
          <Link
            href="/about"
            className="text-accent hover:underline underline-offset-2"
          >
            About
          </Link>
          .
        </p>
      </section>
    </article>
  );
}
