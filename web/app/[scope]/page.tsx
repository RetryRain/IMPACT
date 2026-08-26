import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FeedDateNav } from "@/components/FeedDateNav";
import { FadingIntro } from "@/components/FadingIntro";
import { FeedList } from "@/components/FeedList";
import { Pagination } from "@/components/Pagination";
import { parseCategorySearchParams } from "@/lib/categories";
import { parseFeedDateParam } from "@/lib/feed-dates";
import { parseFeedSortParam } from "@/lib/feed-sort";
import { getFeedStories, getFeedStoryDates } from "@/lib/queries";
import {
  isScopePath,
  SCOPE_LABELS,
  scopeFeedSubtitle,
  type ScopePath,
} from "@/lib/scope";
import { absoluteUrl } from "@/lib/site";

export const dynamic = "force-dynamic";
export const revalidate = 60;

type PageProps = {
  params: Promise<{ scope: string }>;
  searchParams: Promise<{ page?: string; date?: string; sort?: string; category?: string | string[] }>;
};

const SCOPE_META: Record<ScopePath, { title: string; description: string }> = {
  "tamil-nadu": {
    title: "Tamil Nadu news",
    description:
      "Tamil Nadu news from TNDecaf. State stories on government, services, and daily life.",
  },
  india: {
    title: "India news",
    description:
      "National news from TNDecaf. Quality India coverage without engagement bait or filler.",
  },
  world: {
    title: "World news",
    description:
      "Global news from TNDecaf. International stories that matter, free to read.",
  },
};

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { scope } = await params;
  if (!isScopePath(scope)) {
    return { title: "Not found" };
  }
  const meta = SCOPE_META[scope];
  return {
    title: meta.title,
    description: meta.description,
    alternates: { canonical: absoluteUrl(`/${scope}`) },
  };
}

export default async function ScopeFeedPage({ params, searchParams }: PageProps) {
  const { scope } = await params;
  if (!isScopePath(scope)) {
    notFound();
  }

  const query = await searchParams;
  const page = Math.max(1, Number(query.page ?? "1") || 1);
  const selectedDate = parseFeedDateParam(query.date);
  const selectedSort = parseFeedSortParam(query.sort);
  const categories = parseCategorySearchParams(query);
  const scopePath = scope as ScopePath;
  const [feed, dates] = await Promise.all([
    getFeedStories(scopePath, page, selectedDate, selectedSort, categories),
    getFeedStoryDates(scopePath, categories),
  ]);
  const label = SCOPE_LABELS[scope];
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
          {label}
        </h1>
        <FadingIntro className="mt-3">
          {scopeFeedSubtitle(scopePath)}
        </FadingIntro>
      </header>
      <FeedDateNav
        basePath={`/${scope}`}
        dates={dates}
        selectedDate={selectedDate}
        selectedSort={selectedSort}
      />
      <FeedList stories={feed.stories} />
      <Pagination
        basePath={`/${scope}`}
        page={feed.page}
        totalPages={feed.totalPages}
        query={paginationQuery}
      />
    </div>
  );
}
