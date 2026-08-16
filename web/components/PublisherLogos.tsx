import type { ResolvedPublisher } from "@/lib/publishers";
import { allPublishers } from "@/lib/publishers";

type PublisherLogosProps = {
  publishers?: ResolvedPublisher[];
  linked?: boolean;
  className?: string;
  /** Larger slots for About page */
  variant?: "default" | "prominent";
};

function PublisherLogoSlot({
  publisher,
  linked,
  variant,
}: {
  publisher: ResolvedPublisher;
  linked?: boolean;
  variant: "default" | "prominent";
}) {
  const slotClass =
    variant === "prominent" ? "h-8 w-28" : "h-6 w-24";
  const imgClass =
    variant === "prominent" ? "h-8" : "h-6";

  const mark = (
    <div
      className={`${slotClass} flex shrink-0 items-center justify-center text-ink`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={publisher.asset}
        alt=""
        className={`${imgClass} w-full object-contain object-center grayscale`}
      />
    </div>
  );

  const wrapperClass =
    "group opacity-40 hover:opacity-70 transition-opacity";

  if (linked && publisher.url) {
    return (
      <a
        href={publisher.url}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={publisher.label}
        className={wrapperClass}
      >
        {mark}
      </a>
    );
  }

  return (
    <div
      aria-label={publisher.label}
      title={publisher.label}
      className={wrapperClass}
    >
      {mark}
    </div>
  );
}

export function PublisherLogos({
  publishers,
  linked = false,
  className = "",
  variant = "default",
}: PublisherLogosProps) {
  const items = publishers ?? allPublishers();
  const gapClass =
    variant === "prominent"
      ? "gap-x-6 gap-y-4 sm:gap-x-8"
      : "gap-x-4 gap-y-3";

  return (
    <div
      className={`flex flex-wrap items-center ${gapClass} ${className}`}
    >
      {items.map((publisher) => (
        <PublisherLogoSlot
          key={publisher.id}
          publisher={publisher}
          linked={linked}
          variant={variant}
        />
      ))}
    </div>
  );
}
