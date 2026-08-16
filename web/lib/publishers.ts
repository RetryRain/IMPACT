export type PublisherId = "hindu" | "indian-express" | "times-of-india";

export type ResolvedPublisher = {
  id: PublisherId;
  label: string;
  asset: string;
  url?: string;
};

export const PUBLISHERS: Record<
  PublisherId,
  { label: string; asset: string }
> = {
  hindu: {
    label: "The Hindu",
    asset: "/publishers/the-hindu.svg",
  },
  "indian-express": {
    label: "The Indian Express",
    asset: "/publishers/indian-express.svg",
  },
  "times-of-india": {
    label: "The Times of India",
    asset: "/publishers/times-of-india.svg",
  },
};

export const ALL_PUBLISHER_IDS: PublisherId[] = [
  "hindu",
  "indian-express",
  "times-of-india",
];

const NAME_TO_ID: Record<string, PublisherId> = {
  "the hindu": "hindu",
  hindu: "hindu",
  "the indian express": "indian-express",
  "indian express": "indian-express",
  "the new indian express": "indian-express",
  "new indian express": "indian-express",
  "the times of india": "times-of-india",
  "times of india": "times-of-india",
  toi: "times-of-india",
};

const HOST_PATTERNS: Array<{ pattern: string; id: PublisherId }> = [
  { pattern: "thehindu.com", id: "hindu" },
  { pattern: "indianexpress.com", id: "indian-express" },
  { pattern: "newindianexpress.com", id: "indian-express" },
  { pattern: "timesofindia.com", id: "times-of-india" },
  { pattern: "indiatimes.com", id: "times-of-india" },
];

function publisherFromHostname(hostname: string): PublisherId | null {
  const host = hostname.toLowerCase().replace(/^www\./, "");
  for (const { pattern, id } of HOST_PATTERNS) {
    if (host === pattern || host.endsWith(`.${pattern}`)) {
      return id;
    }
  }
  return null;
}

function publisherFromUrl(url: string): PublisherId | null {
  try {
    return publisherFromHostname(new URL(url).hostname);
  } catch {
    return null;
  }
}

export function resolvePublisherId(nameOrUrl: string): PublisherId | null {
  const trimmed = nameOrUrl.trim();
  if (!trimmed) return null;

  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return publisherFromUrl(trimmed);
  }

  return NAME_TO_ID[trimmed.toLowerCase()] ?? null;
}

export function resolveStoryPublishers(
  sources: string[],
  sourceUrls: string[],
): ResolvedPublisher[] {
  const byId = new Map<PublisherId, ResolvedPublisher>();

  for (const url of sourceUrls) {
    const id = publisherFromUrl(url);
    if (!id) continue;

    const existing = byId.get(id);
    if (!existing) {
      byId.set(id, { id, ...PUBLISHERS[id], url });
    }
  }

  for (const name of sources) {
    const id = resolvePublisherId(name);
    if (!id) continue;

    const existing = byId.get(id);
    if (existing) continue;

    const matchingUrl = sourceUrls.find((url) => publisherFromUrl(url) === id);
    byId.set(id, {
      id,
      ...PUBLISHERS[id],
      url: matchingUrl,
    });
  }

  return ALL_PUBLISHER_IDS.filter((id) => byId.has(id)).map(
    (id) => byId.get(id)!,
  );
}

export function allPublishers(): ResolvedPublisher[] {
  return ALL_PUBLISHER_IDS.map((id) => ({ id, ...PUBLISHERS[id] }));
}
