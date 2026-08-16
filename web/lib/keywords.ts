export function storyKeywords(
  tags: string[] | null | undefined,
): string | undefined {
  if (!tags?.length) return undefined;
  return tags.join(", ");
}
