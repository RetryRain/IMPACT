import type { Metadata } from "next";
import { FeedDateNav } from "@/components/FeedDateNav";
import { FeedList } from "@/components/FeedList";
import { FadingIntro } from "@/components/FadingIntro";
import { Pagination } from "@/components/Pagination";
import { parseCategorySearchParams } from "@/lib/categories";
import { parseFeedDateParam } from "@/lib/feed-dates";
import { parseFeedSortParam } from "@/lib/feed-sort";
import { getFeedStories, getFeedStoryDates } from "@/lib/queries";
import { absoluteUrl } from "@/lib/site";

export const dynamic = "force-dynamic";
export const revalidate = 60;

type PageProps = {
  searchParams: Promise<{ page?: string; date?: string; sort?: string; category?: string | string[] }>;
};

export const metadata: Metadata = {
  title: "Today's briefing",
  description:
    "Today's news briefing from TNDecaf. Tamil Nadu, India, and world stories without clickbait. Free, no ads, no account.",
  alternates: { canonical: absoluteUrl("/") },
};

export default async function HomePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const selectedDate = parseFeedDateParam(params.date);
  const selectedSort = parseFeedSortParam(params.sort);
  const categories = parseCategorySearchParams(params);
  const [feed, dates] = await Promise.all([
    getFeedStories(undefined, page, selectedDate, selectedSort, categories),
    getFeedStoryDates(undefined, categories),
  ]);

  const categoryQuery =
    categories.length > 0 ? { category: categories } : undefined;
  const paginationQuery =
    selectedSort === "latest"
      ? { sort: "latest" as const, ...categoryQuery }
      : selectedDate
        ? { date: selectedDate, ...categoryQuery }
        : categoryQuery;

  return (
    <div>
      <header className="mb-8 max-w-article">
        <h1 className="font-serif text-3xl sm:text-4xl font-bold text-ink leading-tight">
          Today&apos;s briefing
        </h1>
        <FadingIntro className="mt-3">
          Tamil Nadu, India, and world — quality stories without bait,
          outrage farming, or extra headlines.
        </FadingIntro>
      </header>
      <FeedDateNav
        basePath="/"
        dates={dates}
        selectedDate={selectedDate}
        selectedSort={selectedSort}
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
