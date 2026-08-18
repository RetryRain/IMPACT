import Link from "next/link";

type PaginationProps = {
  basePath: string;
  page: number;
  totalPages: number;
  query?: Record<string, string | undefined>;
};

function buildPageHref(
  basePath: string,
  page: number,
  query?: Record<string, string | undefined>,
): string {
  const params = new URLSearchParams();
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value) params.set(key, value);
    }
  }
  if (page > 1) {
    params.set("page", String(page));
  }
  const qs = params.toString();
  return qs ? `${basePath}?${qs}` : basePath;
}

export function Pagination({
  basePath,
  page,
  totalPages,
  query,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  const prevPage = page > 1 ? page - 1 : null;
  const nextPage = page < totalPages ? page + 1 : null;

  return (
    <nav
      className="mt-10 flex items-center justify-between font-sans text-sm"
      aria-label="Pagination"
    >
      <div>
        {prevPage ? (
          <Link
            href={buildPageHref(basePath, prevPage, query)}
            rel="prev"
            className="text-accent hover:underline"
          >
            ← Previous
          </Link>
        ) : (
          <span className="text-muted">← Previous</span>
        )}
      </div>
      <span className="text-muted">
        Page {page} of {totalPages}
      </span>
      <div>
        {nextPage ? (
          <Link
            href={buildPageHref(basePath, nextPage, query)}
            rel="next"
            className="text-accent hover:underline"
          >
            Next →
          </Link>
        ) : (
          <span className="text-muted">Next →</span>
        )}
      </div>
    </nav>
  );
}
