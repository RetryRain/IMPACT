import type { Metadata } from "next";
import { FeedList } from "@/components/FeedList";
import { FadingIntro } from "@/components/FadingIntro";
import { Pagination } from "@/components/Pagination";
import { getFeedStories } from "@/lib/queries";
import { absoluteUrl } from "@/lib/site";

export const dynamic = "force-dynamic";
export const revalidate = 60;

type PageProps = {
  searchParams: Promise<{ page?: string }>;
};

export const metadata: Metadata = {
  title: "Today in Tamil Nadu",
  description:
    "Tamil Nadu news briefing from TNDrops. Short original stories on work, money, safety, and community. Free, no ads, no account.",
  alternates: { canonical: absoluteUrl("/") },
};

export default async function HomePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const feed = await getFeedStories(undefined, page);

  return (
    <div>
      <header className="mb-8 max-w-article">
        <h1 className="font-serif text-3xl sm:text-4xl font-bold text-ink leading-tight">
          Today in Tamil Nadu
        </h1>
        <FadingIntro className="mt-3">
          Short original stories on what affects life here. No celebrity bait, no
          outrage farming, no extra headlines.
        </FadingIntro>
      </header>
      <FeedList stories={feed.stories} />
      <Pagination basePath="/" page={feed.page} totalPages={feed.totalPages} />
    </div>
  );
}
