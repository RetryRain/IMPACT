import type { Metadata } from "next";
import { FeedList } from "@/components/FeedList";
import { Pagination } from "@/components/Pagination";
import { getFeedStories } from "@/lib/queries";
import { absoluteUrl } from "@/lib/site";

export const dynamic = "force-dynamic";
export const revalidate = 60;

type PageProps = {
  searchParams: Promise<{ page?: string }>;
};

export const metadata: Metadata = {
  title: "What matters in Tamil Nadu today",
  description:
    "Latest Bytez stories ranked by relevance to Tamil Nadu readers.",
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
          What matters in Tamil Nadu today
        </h1>
        <p className="mt-3 font-sans text-muted leading-relaxed">
          Synthesized from multiple sources. Filtered for practical relevance —
          not everything in the news.
        </p>
      </header>
      <FeedList stories={feed.stories} />
      <Pagination basePath="/" page={feed.page} totalPages={feed.totalPages} />
    </div>
  );
}
