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
  title: "My signal. Not your noise.",
  description:
    "TNforME stories ranked by how much they could affect your life in Tamil Nadu.",
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
          My signal. Not your noise.
        </h1>
        <p className="mt-3 font-sans text-muted leading-relaxed">
          TNforME doesn&apos;t give you more headlines. It gives you a clearer
          picture of what affects <em>your</em> life in Tamil Nadu.
        </p>
      </header>
      <FeedList stories={feed.stories} />
      <Pagination basePath="/" page={feed.page} totalPages={feed.totalPages} />
    </div>
  );
}
