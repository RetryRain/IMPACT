import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FadingIntro } from "@/components/FadingIntro";
import { FeedList } from "@/components/FeedList";
import { Pagination } from "@/components/Pagination";
import { getFeedStories } from "@/lib/queries";
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
  searchParams: Promise<{ page?: string }>;
};

const SCOPE_META: Record<ScopePath, { title: string; description: string }> = {
  "tamil-nadu": {
    title: "Tamil Nadu news",
    description:
      "Tamil Nadu news for local readers from TNDrops. State stories on work, money, safety, and public services.",
  },
  india: {
    title: "India news for Tamil Nadu readers",
    description:
      "National news from TNDrops when it changes life in Tamil Nadu. No engagement bait, no filler.",
  },
  world: {
    title: "World news for Tamil Nadu readers",
    description:
      "Global news from TNDrops when it reaches Tamil Nadu. Short original briefs, free to read.",
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
  const feed = await getFeedStories(scope as ScopePath, page);
  const label = SCOPE_LABELS[scope];

  return (
    <div>
      <header className="mb-8 max-w-article">
        <h1 className="font-serif text-3xl sm:text-4xl font-bold text-ink leading-tight">
          {label}
        </h1>
        <FadingIntro className="mt-3">
          {scopeFeedSubtitle(scope as ScopePath)}
        </FadingIntro>
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
