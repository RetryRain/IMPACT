import type { Metadata } from "next";
import { FeedDateNav } from "@/components/FeedDateNav";
import { FeedList } from "@/components/FeedList";
import { FadingIntro } from "@/components/FadingIntro";
import { Pagination } from "@/components/Pagination";
import { parseFeedDateParam } from "@/lib/feed-dates";
import { getFeedStories, getFeedStoryDates } from "@/lib/queries";
import { absoluteUrl } from "@/lib/site";

export const dynamic = "force-dynamic";
export const revalidate = 60;

type PageProps = {
  searchParams: Promise<{ page?: string; date?: string }>;
};

export const metadata: Metadata = {
  title: "Today in Tamil Nadu",
  description:
    "Tamil Nadu news briefing from TNDecaf. Short original stories on work, money, safety, and community. Free, no ads, no account.",
  alternates: { canonical: absoluteUrl("/") },
};

export default async function HomePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const selectedDate = parseFeedDateParam(params.date);
  const [feed, dates] = await Promise.all([
    getFeedStories(undefined, page, selectedDate),
    getFeedStoryDates(),
  ]);

  const paginationQuery = selectedDate ? { date: selectedDate } : undefined;

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
      <FeedDateNav
        basePath="/"
        dates={dates}
        selectedDate={selectedDate}
      />
      <FeedList stories={feed.stories} />
      <Pagination
        basePath="/"
        page={feed.page}
        totalPages={feed.totalPages}
        query={paginationQuery}
      />
    </div>
  );
}
