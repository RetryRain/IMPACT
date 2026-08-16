import { FeedSkeleton } from "@/components/FeedSkeleton";

export default function ScopeFeedLoading() {
  return (
    <div>
      <header className="mb-8 max-w-article animate-pulse" aria-hidden="true">
        <div className="h-9 w-32 rounded bg-border sm:h-10" />
        <div className="mt-3 h-4 w-full max-w-lg rounded bg-border" />
      </header>
      <FeedSkeleton />
    </div>
  );
}
