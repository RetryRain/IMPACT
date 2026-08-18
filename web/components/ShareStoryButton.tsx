"use client";

import { useCallback, useState } from "react";

type ShareStoryButtonProps = {
  title: string;
  url: string;
};

function ShareIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <path
        d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7M16 6l-4-4-4 4M12 2v14"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ShareStoryButton({ title, url }: ShareStoryButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleShare = useCallback(async () => {
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ title, url });
        return;
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
      }
    }

    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      window.prompt("Copy this link:", url);
    }
  }, [title, url]);

  return (
    <button
      type="button"
      onClick={handleShare}
      className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-accent/30 bg-accent-soft text-accent transition-colors hover:border-accent/50 hover:bg-accent/10"
      aria-label={copied ? "Link copied" : "Share this story"}
      title={copied ? "Copied" : "Share"}
    >
      <ShareIcon className="h-4 w-4" />
    </button>
  );
}
