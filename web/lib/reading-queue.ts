const QUEUE_KEY = "tndecaf:reading-queue";

export type ReadingQueueItem = {
  id: string;
  slug: string;
  scope: string;
  title?: string;
};

export function saveReadingQueue(items: ReadingQueueItem[]): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(QUEUE_KEY, JSON.stringify(items));
}

export function getReadingQueue(): ReadingQueueItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(QUEUE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ReadingQueueItem[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function findQueueIndex(
  queue: ReadingQueueItem[],
  scope: string,
  slug: string,
): number {
  return queue.findIndex((item) => item.scope === scope && item.slug === slug);
}
