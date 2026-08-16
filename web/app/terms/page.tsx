import type { Metadata } from "next";
import Link from "next/link";
import { SITE_NAME, absoluteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "Terms",
  description:
    "Terms of use for TNforME — free, independent Tamil Nadu news curation.",
  alternates: { canonical: absoluteUrl("/terms") },
};

export default function TermsPage() {
  return (
    <article className="mx-auto max-w-article font-sans text-muted leading-relaxed space-y-6">
      <h1 className="font-serif text-4xl font-bold text-ink tracking-tight">
        Terms of use
      </h1>
      <p className="text-lg">
        {SITE_NAME} is a free, independent news filter for people in Tamil Nadu.
        By using the site, you agree to these plain terms.
      </p>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-bold text-ink">Free service</h2>
        <p>
          {SITE_NAME} is provided at no cost. There are no subscriptions, no
          paywalls, and no ads. We may change features over time, but the core
          feed stays free.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-bold text-ink">
          Independent, not affiliated
        </h2>
        <p>
          We are not owned by, affiliated with, or endorsed by The Hindu, The
          Indian Express, The Times of India, or any other publisher we cite.
          Publisher logos are shown for identification only.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-bold text-ink">
          Original briefs from public reporting
        </h2>
        <p>
          Stories on {SITE_NAME} are original briefs written from publicly
          available reporting. We synthesize facts and cite sources — we do not
          copy full articles or speak on behalf of publishers.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-bold text-ink">
          TN-impact filter
        </h2>
        <p>
          We rank and include stories based on how much they may affect daily life
          in Tamil Nadu. India and world news appears when it has local impact.
          That editorial choice is ours — not a guarantee that every story
          matters to every reader.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-bold text-ink">No warranty</h2>
        <p>
          News moves fast. We work to be accurate and timely, but we don&apos;t
          guarantee completeness or that every detail is current. For official
          or legal decisions, verify with primary sources and professional
          advice.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-bold text-ink">Questions</h2>
        <p>
          See{" "}
          <Link
            href="/privacy"
            className="text-accent hover:underline underline-offset-2"
          >
            Privacy
          </Link>{" "}
          or{" "}
          <Link
            href="/about"
            className="text-accent hover:underline underline-offset-2"
          >
            About
          </Link>
          . Feedback is in the site footer.
        </p>
      </section>
    </article>
  );
}
