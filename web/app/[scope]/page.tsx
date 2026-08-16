import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FeedList } from "@/components/FeedList";
import { Pagination } from "@/components/Pagination";
import { getFeedStories } from "@/lib/queries";
import {
  isScopePath,
  SCOPE_LABELS,
  type ScopePath,
} from "@/lib/scope";
import { absoluteUrl } from "@/lib/site";

export const dynamic = "force-dynamic";
export const revalidate = 60;

type PageProps = {
  params: Promise<{ scope: string }>;
  searchParams: Promise<{ page?: string }>;
};

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { scope } = await params;
  if (!isScopePath(scope)) {
    return { title: "Not found" };
  }
  const label = SCOPE_LABELS[scope];
  return {
    title: `${label} news`,
    description: `TNforME stories about ${label}, ranked by how much they could affect your life in Tamil Nadu.`,
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
  const feed = await getFeedStories(scope as ScopePath, page);
  const label = SCOPE_LABELS[scope];

  return (
    <div>
      <header className="mb-8 max-w-article">
        <h1 className="font-serif text-3xl sm:text-4xl font-bold text-ink leading-tight">
          {label}
        </h1>
        <p className="mt-3 font-sans text-muted leading-relaxed">
          Signal for <em>your</em> Tamil Nadu — not every headline about{" "}
          {label}.
        </p>
      </header>
      <FeedList stories={feed.stories} />
      <Pagination
        basePath={`/${scope}`}
        page={feed.page}
        totalPages={feed.totalPages}
      />
    </div>
  );
}
