import type { ResolvedPublisher } from "@/lib/publishers";
import { allPublishers } from "@/lib/publishers";

type PublisherLogosProps = {
  publishers?: ResolvedPublisher[];
  linked?: boolean;
  className?: string;
};

function PublisherLogoSlot({
  publisher,
  linked,
}: {
  publisher: ResolvedPublisher;
  linked?: boolean;
}) {
  const mark = (
    <div className="h-10 w-40 flex shrink-0 items-center justify-center text-ink">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={publisher.asset}
        alt=""
        className="h-10 w-full object-contain object-center opacity-70 grayscale"
      />
    </div>
  );

  if (linked && publisher.url) {
    return (
      <a
        href={publisher.url}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={publisher.label}
        className="hover:opacity-90 transition-opacity"
      >
        {mark}
      </a>
    );
  }

  return (
    <div aria-label={publisher.label} title={publisher.label}>
      {mark}
    </div>
  );
}

export function PublisherLogos({
  publishers,
  linked = false,
  className = "",
}: PublisherLogosProps) {
  const items = publishers ?? allPublishers();

  return (
    <div
      className={`flex flex-wrap items-center justify-center gap-x-8 gap-y-6 sm:gap-x-12 ${className}`}
    >
      {items.map((publisher) => (
        <PublisherLogoSlot
          key={publisher.id}
          publisher={publisher}
          linked={linked}
        />
      ))}
    </div>
  );
}
