export const SCOPE_PATHS = ["tamil-nadu", "india", "world"] as const;

export type ScopePath = (typeof SCOPE_PATHS)[number];

export const SCOPE_LABELS: Record<ScopePath, string> = {
  "tamil-nadu": "Tamil Nadu",
  india: "India",
  world: "World",
};

export const LABEL_TO_PATH: Record<string, ScopePath> = {
  "Tamil Nadu": "tamil-nadu",
  India: "india",
  World: "world",
};

export function scopeToPath(scope: string | null | undefined): ScopePath | null {
  if (!scope) return null;
  return LABEL_TO_PATH[scope] ?? null;
}

export function pathToScopeLabel(path: string): string | null {
  if (path in SCOPE_LABELS) {
    return SCOPE_LABELS[path as ScopePath];
  }
  return null;
}

export function isScopePath(path: string): path is ScopePath {
  return (SCOPE_PATHS as readonly string[]).includes(path);
}

export function storyPath(scopePath: ScopePath, slug: string): string {
  return `/${scopePath}/${slug}`;
}
