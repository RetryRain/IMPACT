import type { Metadata } from "next";
import Link from "next/link";
import { PublisherLogos } from "@/components/PublisherLogos";
import { SITE_DESCRIPTION, SITE_NAME, absoluteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "About",
  description:
    "About TNDecaf: free Tamil Nadu news without engagement bait. Short original stories on work, money, safety, and public life.",
  alternates: { canonical: absoluteUrl("/about") },
};

function SectionLabel({ children }: { children: string }) {
  return (
    <p className="font-sans text-xs font-medium uppercase tracking-[0.2em] text-accent-ink mb-6">
      {children}
    </p>
  );
}

export default function AboutPage() {
  return (
    <div className="-my-8">
      <section className="pt-8 sm:pt-16 pb-16 sm:pb-24">
        <div className="mx-auto max-w-article text-center">
          <p className="font-sans text-xs font-medium uppercase tracking-[0.2em] text-accent-ink">
            {SITE_NAME} · 100% free · no ads
          </p>
          <h1 className="mt-6 font-serif text-4xl sm:text-5xl lg:text-6xl font-bold text-ink tracking-tight leading-[1.1]">
            Tamil Nadu news.
            <br />
            Without the bait.
          </h1>
          <div
            className="mx-auto mt-6 h-[3px] w-24 bg-accent rounded-full"
            aria-hidden="true"
          />
          <p className="mt-8 font-sans text-lg sm:text-xl text-muted leading-relaxed">
            {SITE_DESCRIPTION} India and world coverage appears only when it
            reaches life here. Think of it as decaf news: the signal, without the
            outrage caffeine.
          </p>
          <div className="mt-10">
            <Link
              href="/"
              className="inline-flex items-center font-sans text-sm font-medium text-paper bg-accent px-6 py-3 rounded-full hover:bg-accent/90 transition-colors"
            >
              Read today&apos;s Tamil Nadu briefing
            </Link>
            <p className="mt-4 font-sans text-sm text-muted">
              Free forever · Updated throughout the day
            </p>
          </div>
        </div>
      </section>

      <section className="py-16 sm:py-24 border-t border-border">
        <div className="mx-auto max-w-article">
          <SectionLabel>Who we are</SectionLabel>
          <h2 className="font-serif text-3xl sm:text-4xl font-bold text-ink tracking-tight leading-tight mb-8">
            A Tamil Nadu news briefing, not a scroll trap
          </h2>
          <div className="font-sans text-lg text-muted leading-relaxed space-y-6">
            <p>
              {SITE_NAME} is for people in Tamil Nadu who want to stay informed
              without living inside a news feed. We publish short original
              stories on work, money, safety, and public services.
            </p>
            <p>
              We drop gossip, speeches-for-the-camera, and distant outrage. We
              do not rank by celebrity, outrage, or click potential. If it does
              not affect people in Tamil Nadu, it is not here.
            </p>
          </div>
        </div>
      </section>

      <section className="py-16 sm:py-24 border-t border-border">
        <div className="mx-auto max-w-article mb-12 sm:mb-16 text-center">
          <SectionLabel>What you get</SectionLabel>
          <h2 className="font-serif text-3xl sm:text-4xl font-bold text-ink tracking-tight leading-tight">
            Less noise. More clarity.
          </h2>
        </div>
        <div className="grid gap-12 sm:gap-16 sm:grid-cols-3">
          <div>
            <p className="font-sans text-xs font-medium uppercase tracking-[0.15em] text-accent mb-4">
              01
            </p>
            <h3 className="font-serif text-xl sm:text-2xl font-bold text-ink mb-4">
              One place to read
            </h3>
            <p className="font-sans text-base text-muted leading-relaxed">
              We follow established national and regional papers so you are not
              jumping between tabs all morning.
            </p>
          </div>
          <div>
            <p className="font-sans text-xs font-medium uppercase tracking-[0.15em] text-accent mb-4">
              02
            </p>
            <h3 className="font-serif text-xl sm:text-2xl font-bold text-ink mb-4">
              Short original stories
            </h3>
            <p className="font-sans text-base text-muted leading-relaxed">
              Each item is a brief written for this site: clear, factual, and
              grounded in public reporting.
            </p>
          </div>
          <div>
            <p className="font-sans text-xs font-medium uppercase tracking-[0.15em] text-accent mb-4">
              03
            </p>
            <h3 className="font-serif text-xl sm:text-2xl font-bold text-ink mb-4">
              Relevant by default
            </h3>
            <p className="font-sans text-base text-muted leading-relaxed">
              Every story is chosen and written with Tamil Nadu in mind. If it
              does not land on life here, it is not in the feed.
            </p>
          </div>
        </div>
      </section>

      <section className="py-12 sm:py-16 border-t border-border">
        <div className="mx-auto max-w-article rounded-2xl bg-accent-soft px-6 py-10 sm:px-10 sm:py-12">
          <h2 className="font-serif text-2xl sm:text-3xl font-bold text-ink tracking-tight leading-tight">
            Engineered for clarity. Edited for trust.
          </h2>
          <p className="mt-4 font-sans text-base sm:text-lg text-muted leading-relaxed">
            <strong className="text-ink font-semibold">We use algorithms to fight algorithms.</strong>{" "}
            While newsfeed algorithms are engineered to farm outrage, our tools fight back — neutralizing clickbait and filtering for real-world impact so nothing slips through. We verify the facts and write clear, fluff-free updates for Tamil Nadu.
          </p>
        </div>
      </section>

      <section className="py-12 sm:py-16 border-t border-border">
        <div className="mx-auto max-w-article rounded-2xl border border-border px-6 py-10 sm:px-10 sm:py-12 text-center">
          <h2 className="font-serif text-2xl sm:text-3xl font-bold text-ink tracking-tight leading-tight">
            Free. No ads. No rage ranking.
          </h2>
          <p className="mt-4 font-sans text-base sm:text-lg text-muted leading-relaxed max-w-2xl mx-auto">
            No subscription traps, no hidden paywalls, and no sponsored clutter.{" "}
            {SITE_NAME} is built to respect your time, not farm your attention.
          </p>
        </div>
      </section>

      <section className="py-16 sm:py-24 border-t border-border">
        <div className="mx-auto max-w-article text-center">
          <SectionLabel>Sources we use</SectionLabel>
          <h2 className="font-serif text-3xl sm:text-4xl font-bold text-ink tracking-tight leading-tight mb-6">
            Built on trusted reporting
          </h2>
          <p className="font-sans text-lg text-muted leading-relaxed mb-12 max-w-2xl mx-auto">
            We draw on public reporting from established outlets including{" "}
            <strong className="text-ink">The Hindu</strong>,{" "}
            <strong className="text-ink">The Indian Express</strong>, and{" "}
            <strong className="text-ink">The Times of India</strong>. Stories
            cite those sources clearly. We do not copy full articles or speak on
            their behalf.
          </p>
          <PublisherLogos
            variant="prominent"
            className="justify-center"
          />
          <p className="mt-10 font-sans text-sm text-muted">
            Logos shown for identification only. {SITE_NAME} is independent and
            not affiliated with or endorsed by these publishers.
          </p>
        </div>
      </section>

      <section className="py-16 sm:py-24 border-t border-border">
        <div className="mx-auto max-w-article text-center">
          <h2 className="font-serif text-3xl sm:text-4xl font-bold text-ink tracking-tight leading-tight mb-6">
            Start with today&apos;s briefing
          </h2>
          <p className="font-sans text-lg text-muted leading-relaxed mb-10 max-w-2xl mx-auto">
            Tamil Nadu, India, and world stories when they matter here. Free to
            read. No account required.
          </p>
          <Link
            href="/"
            className="inline-flex items-center font-sans text-sm font-medium text-paper bg-accent px-6 py-3 rounded-full hover:bg-accent/90 transition-colors"
          >
            Read today&apos;s Tamil Nadu briefing
          </Link>
        </div>
      </section>
    </div>
  );
}
