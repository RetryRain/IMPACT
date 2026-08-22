"use client";

import { useCallback, useEffect, useState } from "react";
import { SITE_NAME } from "@/lib/site";
import {
  PWA_INSTALLED_KEY,
  recordSiteVisit,
  shouldShowInstallBanner,
} from "@/lib/visited-store";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

type NavigatorWithInstalledApps = Navigator & {
  standalone?: boolean;
  getInstalledRelatedApps?: () => Promise<Array<{ id?: string }>>;
};

function isStandaloneMode(): boolean {
  if (typeof window === "undefined") return false;
  const nav = navigator as NavigatorWithInstalledApps;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    nav.standalone === true
  );
}

function isMobileDevice(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(max-width: 767px)").matches ||
    window.matchMedia("(pointer: coarse)").matches
  );
}

function isIosSafari(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  return /iPad|iPhone|iPod/.test(ua) && !(window as Window & { MSStream?: unknown }).MSStream;
}

async function detectInstalledPwa(): Promise<boolean> {
  if (typeof window === "undefined") return false;
  if (localStorage.getItem(PWA_INSTALLED_KEY) === "1") return true;
  if (isStandaloneMode()) {
    localStorage.setItem(PWA_INSTALLED_KEY, "1");
    return true;
  }

  const nav = navigator as NavigatorWithInstalledApps;
  if (typeof nav.getInstalledRelatedApps === "function") {
    try {
      const apps = await nav.getInstalledRelatedApps();
      if (apps.length > 0) {
        localStorage.setItem(PWA_INSTALLED_KEY, "1");
        return true;
      }
    } catch {
      // Unsupported or blocked — fall through.
    }
  }

  return false;
}

/**
 * Test install on the deployed HTTPS site — not LAN `npm run dev` (no SW / secure context).
 */
export function InstallBanner() {
  const [visible, setVisible] = useState(false);
  const [showSteps, setShowSteps] = useState(false);
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    let active = true;

    const init = async () => {
      if (!isMobileDevice()) return;
      if (await detectInstalledPwa()) return;
      const visitCount = recordSiteVisit();
      if (!shouldShowInstallBanner(visitCount)) return;
      if (active) setVisible(true);
    };

    init();

    const onInstalled = () => {
      localStorage.setItem(PWA_INSTALLED_KEY, "1");
      setVisible(false);
      setShowSteps(false);
    };

    window.addEventListener("appinstalled", onInstalled);
    return () => {
      active = false;
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      event.preventDefault();
      setDeferredPrompt(event as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const dismiss = useCallback(() => {
    setVisible(false);
    setShowSteps(false);
  }, []);

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      await deferredPrompt.prompt();
      await deferredPrompt.userChoice;
      setDeferredPrompt(null);
      localStorage.setItem(PWA_INSTALLED_KEY, "1");
      setVisible(false);
      setShowSteps(false);
      return;
    }
    setShowSteps(true);
  };

  if (!visible) return null;

  return (
    <div className="mx-auto max-w-5xl px-4 pt-4">
      <div
        className="relative rounded-2xl border border-accent/20 bg-accent-soft px-4 py-4 sm:px-5 sm:py-5"
        role="region"
        aria-label="Add to home screen"
      >
        <button
          type="button"
          onClick={dismiss}
          className="absolute right-3 top-3 text-accent-ink/60 hover:text-accent-ink p-1"
          aria-label="Dismiss"
        >
          <span className="text-lg leading-none" aria-hidden="true">×</span>
        </button>

        <h2 className="font-serif text-lg font-bold text-accent-ink pr-8">
          Add {SITE_NAME} to your home screen
        </h2>
        <p className="mt-2 text-sm text-accent-ink/90 leading-relaxed max-w-xl">
          Open your Tamil Nadu briefing like an app. No tabs, no clutter.
        </p>

        {showSteps ? (
          <div className="mt-4 text-sm text-accent-ink space-y-2">
            {isIosSafari() ? (
              <>
                <p className="font-medium">On iPhone / iPad:</p>
                <ol className="list-decimal list-inside space-y-1 text-accent-ink/90">
                  <li>Tap the Share button in Safari</li>
                  <li>Scroll down and tap &quot;Add to Home Screen&quot;</li>
                  <li>Open {SITE_NAME} from your home screen</li>
                </ol>
              </>
            ) : (
              <>
                <p className="font-medium">Add to home screen:</p>
                <p className="text-accent-ink/90">
                  Open your browser menu (⋮) and choose &quot;Add to Home
                  screen&quot; or &quot;Install app&quot;.
                </p>
              </>
            )}
          </div>
        ) : (
          <button
            type="button"
            onClick={handleInstallClick}
            className="mt-4 inline-flex items-center font-sans text-sm font-medium text-paper bg-accent px-5 py-2.5 rounded-full hover:bg-accent/90 transition-colors"
          >
            Add to home screen
          </button>
        )}
      </div>
    </div>
  );
}
