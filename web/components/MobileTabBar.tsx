"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SCOPE_LABELS, SCOPE_PATHS, type ScopePath } from "@/lib/scope";

function MapPinIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <path
        d="M12 21s7-4.5 7-11a7 7 0 1 0-14 0c0 6.5 7 11 7 11z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="10" r="2.5" />
    </svg>
  );
}

function IndiaIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <rect x="4" y="5" width="16" height="14" rx="2" className="opacity-20" />
      <path d="M4 9h16M4 15h16" className="opacity-40" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="2.5" />
    </svg>
  );
}

function GlobeIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.5 2.8 2.5 14.2 0 18M12 3c-2.5 2.8-2.5 14.2 0 18" />
    </svg>
  );
}

function InfoIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 10v6M12 7h.01" strokeLinecap="round" />
    </svg>
  );
}

const SCOPE_ICONS: Record<ScopePath, typeof MapPinIcon> = {
  "tamil-nadu": MapPinIcon,
  india: IndiaIcon,
  world: GlobeIcon,
};

function tabActive(pathname: string, path: ScopePath): boolean {
  return pathname === `/${path}` || pathname.startsWith(`/${path}/`);
}

export function MobileTabBar() {
  const pathname = usePathname();
  const aboutActive = pathname === "/about";

  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-50 border-t border-border bg-paper/95 backdrop-blur pb-safe"
      aria-label="Mobile navigation"
    >
      <div className="flex items-stretch justify-around max-w-5xl mx-auto">
        {SCOPE_PATHS.map((path) => {
          const active = tabActive(pathname, path);
          const Icon = SCOPE_ICONS[path];
          const label =
            path === "tamil-nadu" ? "TN" : SCOPE_LABELS[path];
          return (
            <Link
              key={path}
              href={`/${path}`}
              className={`flex flex-1 flex-col items-center justify-center gap-0.5 py-2.5 px-1 text-xs font-sans transition-colors ${
                active ? "text-accent" : "text-muted"
              }`}
            >
              <Icon className="h-5 w-5 shrink-0" />
              <span className="truncate max-w-full">{label}</span>
            </Link>
          );
        })}
        <Link
          href="/about"
          className={`flex flex-1 flex-col items-center justify-center gap-0.5 py-2.5 px-1 text-xs font-sans transition-colors ${
            aboutActive ? "text-accent" : "text-muted"
          }`}
        >
          <InfoIcon className="h-5 w-5 shrink-0" />
          <span>About</span>
        </Link>
      </div>
    </nav>
  );
}
