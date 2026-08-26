export const CATEGORY_SLUGS = [
  "politics",
  "economy",
  "crime",
  "courts",
  "tech",
  "health",
  "environment",
  "sports",
  "culture",
  "international",
] as const;

export type CategorySlug = (typeof CATEGORY_SLUGS)[number];

export const CATEGORY_LABELS: Record<CategorySlug, string> = {
  politics: "Politics",
  economy: "Economy",
  crime: "Crime",
  courts: "Courts",
  tech: "Science & tech",
  health: "Health",
  environment: "Environment",
  sports: "Sports",
  culture: "Culture",
  international: "International",
};

export const CATEGORY_FILTER_STORAGE_KEY = "tndecaf:category-filter";

const CATEGORY_CHIP_STYLES: Record<CategorySlug, string> = {
  politics: "bg-violet-100 text-violet-900",
  economy: "bg-amber-100 text-amber-900",
  crime: "bg-red-100 text-red-900",
  courts: "bg-slate-200 text-slate-800",
  tech: "bg-sky-100 text-sky-900",
  health: "bg-emerald-100 text-emerald-900",
  environment: "bg-lime-100 text-lime-900",
  sports: "bg-orange-100 text-orange-900",
  culture: "bg-fuchsia-100 text-fuchsia-900",
  international: "bg-indigo-100 text-indigo-900",
};

export function isCategorySlug(value: string): value is CategorySlug {
  return (CATEGORY_SLUGS as readonly string[]).includes(value);
}

export function categoryLabel(slug: string | null | undefined): string | null {
  if (!slug || !isCategorySlug(slug)) return null;
  return CATEGORY_LABELS[slug];
}

export function categoryChipClass(slug: CategorySlug | string): string {
  const base = "rounded-full px-2 py-0.5 text-xs font-sans";
  if (isCategorySlug(slug)) {
    return `${base} ${CATEGORY_CHIP_STYLES[slug]}`;
  }
  return `${base} bg-border/80 text-ink`;
}

export function parseCategoryParams(values: string[]): CategorySlug[] {
  const seen = new Set<CategorySlug>();
  const result: CategorySlug[] = [];
  for (const value of values) {
    if (isCategorySlug(value) && !seen.has(value)) {
      seen.add(value);
      result.push(value);
    }
  }
  return result;
}

export function parseCategorySearchParams(
  params: Record<string, string | string[] | undefined>,
): CategorySlug[] {
  const raw = params.category;
  if (!raw) return [];
  const values = Array.isArray(raw) ? raw : [raw];
  return parseCategoryParams(values);
}

export function readSavedCategoryFilter(): CategorySlug[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(CATEGORY_FILTER_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parseCategoryParams(parsed.filter((v) => typeof v === "string"));
  } catch {
    return [];
  }
}

export function saveCategoryFilter(categories: CategorySlug[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(CATEGORY_FILTER_STORAGE_KEY, JSON.stringify(categories));
}
