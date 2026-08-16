import type { Metadata } from "next";
import Link from "next/link";
import { PublisherLogos } from "@/components/PublisherLogos";
import { SITE_NAME, absoluteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "About",
  description:
    "TNforME is your filter for Tamil Nadu news — one clear story on what actually affects your life, not every headline.",
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
      {/* Hero */}
      <section className="pt-8 sm:pt-16 pb-16 sm:pb-24">
        <div className="mx-auto max-w-article text-center">
          <p className="font-sans text-xs font-medium uppercase tracking-[0.2em] text-accent-ink">
            100% FREE · NO PAYWALLS · ZERO ADS
          </p>
          <h1 className="mt-6 font-serif text-5xl sm:text-6xl lg:text-7xl font-bold text-ink tracking-tight leading-[1.05]">
            My signal.
            <br />
            Not your noise.
          </h1>
          <div
            className="mx-auto mt-6 h-[3px] w-24 bg-accent rounded-full"
            aria-hidden="true"
          />
          <p className="mt-8 font-sans text-lg sm:text-xl text-muted leading-relaxed">
            {SITE_NAME} doesn&apos;t give you more news —{" "}
            <strong className="text-ink">it gives you back your time</strong>.
            We filter trusted publishers to deliver short, clear updates on what
            directly impacts your work, money, safety, and community in Tamil
            Nadu.
          </p>
          <p className="mt-4 font-sans text-sm text-muted">
            India &amp; World coverage is included strictly when it directly
            impacts life in Tamil Nadu.
          </p>
          <div className="mt-10">
            <Link
              href="/"
              className="inline-flex items-center font-sans text-sm font-medium text-paper bg-accent px-6 py-3 rounded-full hover:bg-accent/90 transition-colors"
            >
              Give me my TN update
            </Link>
            <p className="mt-4 font-sans text-sm text-muted">
              Free forever · Updated throughout the day
            </p>
          </div>
        </div>
      </section>

      {/* Who we are */}
      <section className="py-16 sm:py-24 border-t border-border">
        <div className="mx-auto max-w-article">
          <SectionLabel>Who we are</SectionLabel>
          <h2 className="font-serif text-3xl sm:text-4xl font-bold text-ink tracking-tight leading-tight mb-8">
            Your filter. Not another aggregator.
          </h2>
          <div className="font-sans text-lg text-muted leading-relaxed space-y-6">
            <p>
              We&apos;re built for people in Tamil Nadu who value their time. We
              don&apos;t chase every headline, mirror every feed, or play games
              for clicks.
            </p>
            <p>
              Our rule is simple and uncompromising: if a story doesn&apos;t
              affect your daily life in Tamil Nadu — your commute, your wallet,
              your family&apos;s safety, your public services, or your local
              community — <strong className="text-ink">we drop it.</strong>
            </p>
            <ul className="space-y-2 list-none text-base sm:text-lg">
              <li>
                <span className="text-muted">No</span> routine political
                speeches
              </li>
              <li>
                <span className="text-muted">No</span> celebrity gossip
              </li>
              <li>
                <span className="text-muted">No</span> distant outrage with zero
                local impact
              </li>
              <li>
                <span className="text-ink font-medium">Just</span> pure,
                actionable signal
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* What we do */}
      <section className="py-16 sm:py-24 border-t border-border">
        <div className="mx-auto max-w-article mb-12 sm:mb-16">
          <SectionLabel>What we do</SectionLabel>
          <h2 className="font-serif text-3xl sm:text-4xl font-bold text-ink tracking-tight leading-tight">
            From noise to MY signal. In three steps.
          </h2>
        </div>
        <div className="grid gap-12 sm:gap-16 sm:grid-cols-3">
          <div>
            <p className="font-sans text-xs font-medium uppercase tracking-[0.15em] text-accent mb-4">
              01 — We read the noise
            </p>
            <h3 className="font-serif text-xl sm:text-2xl font-bold text-ink mb-4">
              So you don&apos;t have to
            </h3>
            <p className="font-sans text-base text-muted leading-relaxed">
              We monitor established national dailies and regional outlets with
              strong editorial standards, tracking everything breaking across
              Tamil Nadu.
            </p>
          </div>
          <div>
            <p className="font-sans text-xs font-medium uppercase tracking-[0.15em] text-accent mb-4">
              02 — We find YOUR signal
            </p>
            <h3 className="font-serif text-xl sm:text-2xl font-bold text-ink mb-4">
              One event. Zero duplicates.
            </h3>
            <p className="font-sans text-base text-muted leading-relaxed">
              When five outlets report on the same event, we combine them into a
              single, cohesive brief. No duplicate headlines, no wasted reading.
            </p>
          </div>
          <div>
            <p className="font-sans text-xs font-medium uppercase tracking-[0.15em] text-accent mb-4">
              03 — You get one clear story
            </p>
            <h3 className="font-serif text-xl sm:text-2xl font-bold text-ink mb-4">
              Ranked for your life in TN
            </h3>
            <p className="font-sans text-base text-muted leading-relaxed">
              We write one original, straightforward story and rank it strictly
              by how much it affects your daily life — not by how loudly news
              channels shouted about it.
            </p>
          </div>
        </div>
      </section>

      {/* Reassurance */}
      <section className="py-12 sm:py-16 border-t border-border">
        <div className="mx-auto max-w-article rounded-2xl bg-accent-soft px-6 py-10 sm:px-10 sm:py-12 text-center">
          <h2 className="font-serif text-2xl sm:text-3xl font-bold text-ink tracking-tight leading-tight">
            100% Free of Cost. Zero Algorithmic Rage-Bait.
          </h2>
          <p className="mt-4 font-sans text-base sm:text-lg text-muted leading-relaxed max-w-2xl mx-auto">
            No subscription traps, no hidden paywalls, and no sponsored clutter.
            Just independent curation designed to give you clarity without the
            noise.
          </p>
        </div>
      </section>

      {/* Sources */}
      <section className="py-16 sm:py-24 border-t border-border">
        <div className="mx-auto max-w-article text-center">
          <SectionLabel>Sources we use</SectionLabel>
          <h2 className="font-serif text-3xl sm:text-4xl font-bold text-ink tracking-tight leading-tight mb-6">
            We do the reading. You get the clarity.
          </h2>
          <p className="font-sans text-lg text-muted leading-relaxed mb-12 max-w-2xl mx-auto">
            We pull together reporting from trusted outlets including{" "}
            <strong className="text-ink">The Hindu</strong>,{" "}
            <strong className="text-ink">The Indian Express</strong>, and{" "}
            <strong className="text-ink">The Times of India</strong>. We
            synthesize key facts from their coverage — citing them clearly
            without copy-pasting or speaking on their behalf.
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

      {/* Closing CTA */}
      <section className="py-16 sm:py-24 border-t border-border">
        <div className="mx-auto max-w-article text-center">
          <h2 className="font-serif text-3xl sm:text-4xl font-bold text-ink tracking-tight leading-tight mb-6">
            Stop scrolling. Start knowing.
          </h2>
          <p className="font-sans text-lg text-muted leading-relaxed mb-10">
            Get a clean feed of stories ranked strictly by relevance to your life
            in Tamil Nadu — covering state, national, and global developments.
            <br className="hidden sm:block" />
            <strong className="text-ink">
              No noise. No duplicates. No bullshit. Just what affects you.
            </strong>
          </p>
          <Link
            href="/"
            className="inline-flex items-center font-sans text-sm font-medium text-paper bg-accent px-6 py-3 rounded-full hover:bg-accent/90 transition-colors"
          >
            Give me my TN update
          </Link>
        </div>
      </section>
    </div>
  );
}
