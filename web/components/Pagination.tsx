import Link from "next/link";

type PaginationProps = {
  basePath: string;
  page: number;
  totalPages: number;
};

export function Pagination({ basePath, page, totalPages }: PaginationProps) {
  if (totalPages <= 1) return null;

  const prevPage = page > 1 ? page - 1 : null;
  const nextPage = page < totalPages ? page + 1 : null;

  const pageHref = (p: number) =>
    p === 1 ? basePath : `${basePath}?page=${p}`;

  return (
    <nav
      className="mt-10 flex items-center justify-between font-sans text-sm"
      aria-label="Pagination"
    >
      <div>
        {prevPage ? (
          <Link
            href={pageHref(prevPage)}
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
            href={pageHref(nextPage)}
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
