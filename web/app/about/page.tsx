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
          <h1 className="font-serif text-5xl sm:text-6xl lg:text-7xl font-bold text-ink tracking-tight leading-[1.05]">
            My signal.
            <br />
            Not your noise.
          </h1>
          <div className="mx-auto mt-6 h-[3px] w-24 bg-accent rounded-full" aria-hidden="true" />
          <p className="mt-8 font-sans text-lg sm:text-xl text-muted leading-relaxed">
            {SITE_NAME} doesn&apos;t give you more news. It gives you a clearer
            understanding of what affects <em>your</em> life — your work, your
            money, your safety, your community. We read the trusted publishers.
            We cut the celebrity chatter, the political posturing, and the
            clickbait. We give you <strong className="text-ink">one clear story</strong> on
            what actually matters in Tamil Nadu.
          </p>
          <div className="mt-10">
            <Link
              href="/"
              className="inline-flex items-center font-sans text-sm font-medium text-paper bg-accent px-6 py-3 rounded-full hover:bg-accent/90 transition-colors"
            >
              Give me my TN update
            </Link>
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
              don&apos;t chase every headline or mirror every feed.
            </p>
            <p>
              Our rule is selfish and simple: if a story doesn&apos;t affect your
              daily life in Tamil Nadu — your commute, your wallet, your
              family&apos;s safety, your public services, or your local community
              — <strong className="text-ink">we drop it.</strong>
            </p>
            <p>
              No routine political speeches. No celebrity gossip. No distant
              drama with no local impact. Just signal.
            </p>
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
              We monitor established Indian publishers — national dailies with
              strong editorial standards — and track what&apos;s breaking across
              Tamil Nadu.
            </p>
          </div>
          <div>
            <p className="font-sans text-xs font-medium uppercase tracking-[0.15em] text-accent mb-4">
              02 — We find YOUR signal
            </p>
            <h3 className="font-serif text-xl sm:text-2xl font-bold text-ink mb-4">
              One event. One file.
            </h3>
            <p className="font-sans text-base text-muted leading-relaxed">
              When five articles are all describing the same real-world event,
              we combine them. We don&apos;t waste your time with duplicate
              headlines.
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
              We write one original, straightforward story. We rank it strictly
              by how much it could affect <em>your</em> life in Tamil Nadu — not
              by how many outlets shouted about it.
            </p>
          </div>
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
            We pull together reporting by trusted outlets including The Hindu,
            The Indian Express, and The Times of India. We cite facts from their
            coverage — we don&apos;t speak for them, and we never just copy-paste.
          </p>
          <PublisherLogos />
          <p className="mt-10 font-sans text-sm text-muted">
            Logos shown for identification only. {SITE_NAME} is independent and
            not affiliated with these publishers.
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
            Get your feed of stories ranked by relevance to <em>your</em> Tamil
            Nadu — covering India, state, and world scopes, updated throughout
            the day. No noise. No duplicates. No bullshit. Just what affects{" "}
            <em>you</em>.
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
