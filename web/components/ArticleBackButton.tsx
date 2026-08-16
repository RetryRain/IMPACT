"use client";

type ArticleBackButtonProps = {
  scopePath: string;
  className?: string;
};

export function ArticleBackButton({
  scopePath,
  className = "",
}: ArticleBackButtonProps) {
  const fallback = `/${scopePath}`;

  const handleBack = () => {
    try {
      if (document.referrer) {
        const referrer = new URL(document.referrer);
        if (referrer.origin === window.location.origin) {
          history.back();
          return;
        }
      }
    } catch {
      // ignore invalid referrer
    }
    window.location.href = fallback;
  };

  return (
    <button
      type="button"
      onClick={handleBack}
      className={`inline-flex items-center gap-2 font-sans text-sm text-accent hover:underline ${className}`}
    >
      <span aria-hidden="true">←</span>
      Back to stories
    </button>
  );
}
