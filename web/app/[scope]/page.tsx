import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FeedDateNav } from "@/components/FeedDateNav";
import { FadingIntro } from "@/components/FadingIntro";
import { FeedList } from "@/components/FeedList";
import { Pagination } from "@/components/Pagination";
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
  searchParams: Promise<{ page?: string; date?: string; sort?: string }>;
};

const SCOPE_META: Record<ScopePath, { title: string; description: string }> = {
  "tamil-nadu": {
    title: "Tamil Nadu news",
    description:
      "Tamil Nadu news for local readers from TNDecaf. State stories on work, money, safety, and public services.",
  },
  india: {
    title: "India news for Tamil Nadu readers",
    description:
      "National news from TNDecaf when it changes life in Tamil Nadu. No engagement bait, no filler.",
  },
  world: {
    title: "World news for Tamil Nadu readers",
    description:
      "Global news from TNDecaf when it reaches Tamil Nadu. Short original briefs, free to read.",
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
  const scopePath = scope as ScopePath;
  const [feed, dates] = await Promise.all([
    getFeedStories(scopePath, page, selectedDate, selectedSort),
    getFeedStoryDates(scopePath),
  ]);
  const label = SCOPE_LABELS[scope];
  const paginationQuery =
    selectedSort === "latest"
      ? { sort: "latest" as const }
      : selectedDate
        ? { date: selectedDate }
        : undefined;

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
