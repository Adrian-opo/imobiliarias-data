"use client";

interface PaginationProps {
  currentPage: number;
  lastPage: number;
  total: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({
  currentPage,
  lastPage,
  total,
  onPageChange,
}: PaginationProps) {
  if (lastPage <= 1) return null;

  function getPages(): (number | "...")[] {
    const pages: (number | "...")[] = [];
    const delta = 1;

    if (lastPage <= 7) {
      for (let i = 1; i <= lastPage; i++) pages.push(i);
      return pages;
    }

    pages.push(1);

    if (currentPage > delta + 2) pages.push("...");

    const start = Math.max(2, currentPage - delta);
    const end = Math.min(lastPage - 1, currentPage + delta);

    for (let i = start; i <= end; i++) pages.push(i);

    if (currentPage < lastPage - delta - 1) pages.push("...");

    pages.push(lastPage);

    return pages;
  }

  const pages = getPages();

  return (
    <div className="flex flex-col items-center gap-3 py-8">
      <p className="text-sm text-gray-500">
        {total} imóvel{total !== 1 ? "is" : ""} encontrado{total !== 1 ? "s" : ""}
      </p>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className="btn-ghost disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label="Página anterior"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>

        {pages.map((page, i) =>
          page === "..." ? (
            <span key={`ellipsis-${i}`} className="px-2 text-gray-400">
              ...
            </span>
          ) : (
            <button
              key={page}
              onClick={() => onPageChange(page)}
              className={`inline-flex h-9 w-9 items-center justify-center rounded-lg text-sm font-medium transition-colors ${
                page === currentPage
                  ? "bg-brand-600 text-white"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {page}
            </button>
          )
        )}

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= lastPage}
          className="btn-ghost disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label="Próxima página"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
