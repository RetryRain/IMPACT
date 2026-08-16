export function FeedSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="animate-pulse" aria-hidden="true">
      {Array.from({ length: rows }).map((_, i) => (
        <article
          key={i}
          className="border-b border-border py-6 first:pt-0 gap-4 sm:grid sm:grid-cols-[1fr_200px]"
        >
          <div className="min-w-0">
            <div className="flex gap-2 mb-2">
              <div className="h-5 w-16 rounded-full bg-border" />
              <div className="h-4 w-12 rounded bg-border" />
            </div>
            <div className="h-7 w-full max-w-md rounded bg-border" />
            <div className="mt-2 h-4 w-full rounded bg-border" />
            <div className="mt-2 h-4 w-[80%] max-w-sm rounded bg-border" />
          </div>
          <div className="mt-4 sm:mt-0 aspect-[16/10] rounded-lg bg-border" />
        </article>
      ))}
    </div>
  );
}
