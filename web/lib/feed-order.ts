const FROM_ARTICLE_KEY = "tndrops:from-article";

export function markFeedReturnFromArticle(): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(FROM_ARTICLE_KEY, "1");
}

export function consumeFeedReturnFromArticle(): boolean {
  if (typeof window === "undefined") return false;
  const value = sessionStorage.getItem(FROM_ARTICLE_KEY) === "1";
  sessionStorage.removeItem(FROM_ARTICLE_KEY);
  return value;
}
