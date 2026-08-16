export default function ArticleLoading() {
  return (
    <article
      className="max-w-article mx-auto animate-pulse"
      aria-busy="true"
      aria-label="Loading article"
    >
      <div className="mb-6 h-4 w-24 rounded bg-border" />
      <header className="mb-8">
        <div className="flex gap-2 mb-4">
          <div className="h-5 w-20 rounded-full bg-border" />
          <div className="h-4 w-16 rounded bg-border" />
        </div>
        <div className="h-9 w-full rounded bg-border sm:h-10" />
        <div className="mt-4 h-4 w-full rounded bg-border" />
        <div className="mt-2 h-4 w-[92%] rounded bg-border" />
      </header>
      <div className="aspect-[16/9] rounded-lg bg-border mb-8" />
      <div className="space-y-3">
        <div className="h-4 w-full rounded bg-border" />
        <div className="h-4 w-full rounded bg-border" />
        <div className="h-4 w-10/12 rounded bg-border" />
        <div className="h-4 w-full rounded bg-border" />
        <div className="h-4 w-9/12 rounded bg-border" />
      </div>
    </article>
  );
}
