import { FeedSkeleton } from "@/components/FeedSkeleton";

export default function HomeLoading() {
  return (
    <div>
      <header className="mb-8 max-w-article animate-pulse" aria-hidden="true">
        <div className="h-9 w-64 max-w-full rounded bg-border sm:h-10" />
        <div className="mt-3 h-4 w-full max-w-lg rounded bg-border" />
        <div className="h-4 w-[75%] max-w-md rounded bg-border" />
      </header>
      <FeedSkeleton />
    </div>
  );
}
