export type FeedSort = "priority" | "latest";

export const FEED_SORT_LATEST = "latest";
export const FEED_SORT_LATEST_OPTION = "latest";

export function parseFeedSortParam(value: string | undefined): FeedSort {
  return value === FEED_SORT_LATEST ? "latest" : "priority";
}
