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

const SCOPE_CHIP_STYLES: Record<string, { bg: string; text: string }> = {
  "Tamil Nadu": { bg: "bg-scope-tn-bg", text: "text-scope-tn-text" },
  India: { bg: "bg-scope-india-bg", text: "text-scope-india-text" },
  World: { bg: "bg-scope-world-bg", text: "text-scope-world-text" },
};

/** Scope chip styles for feed cards and article headers. */
export function scopeChipClass(scope: string | null | undefined): string {
  const base = "rounded-full px-2 py-0.5 text-xs font-sans";
  const style = scope ? SCOPE_CHIP_STYLES[scope] : null;
  if (!style) return `${base} bg-border/80 text-ink`;
  return `${base} ${style.bg} ${style.text}`;
}

/** Subtitle for scope feed headers. */
export function scopeFeedSubtitle(scopePath: ScopePath): string {
  switch (scopePath) {
    case "tamil-nadu":
      return "State news that matters — government, services, and daily life here.";
    case "india":
      return "National stories with real consequences. No filler, no outrage bait.";
    case "world":
      return "Global developments worth knowing. Quality over noise.";
  }
}

/** Active nav pill styles per scope path. */
export function scopeNavClass(path: ScopePath, active: boolean): string {
  const base = "px-3 py-1.5 rounded-full transition-colors";
  if (!active) return `${base} text-muted hover:text-ink hover:bg-border/60`;
  const style = SCOPE_CHIP_STYLES[SCOPE_LABELS[path]];
  return `${base} ${style.bg} ${style.text}`;
}
