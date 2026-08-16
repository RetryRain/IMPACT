"use client";

import { useCallback, useEffect, useState } from "react";
import { SITE_NAME } from "@/lib/site";
import { INSTALL_BANNER_DISMISS_KEY } from "@/lib/visited-store";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

function isStandaloneMode(): boolean {
  if (typeof window === "undefined") return false;
  const nav = navigator as Navigator & { standalone?: boolean };
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

/**
 * Test install on the deployed HTTPS site — not LAN `npm run dev` (no SW / secure context).
 */
export function InstallBanner() {
  const [visible, setVisible] = useState(false);
  const [showSteps, setShowSteps] = useState(false);
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    if (!isMobileDevice() || isStandaloneMode()) return;
    if (localStorage.getItem(INSTALL_BANNER_DISMISS_KEY) === "1") return;
    setVisible(true);
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
    localStorage.setItem(INSTALL_BANNER_DISMISS_KEY, "1");
    setVisible(false);
    setShowSteps(false);
  }, []);

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      await deferredPrompt.prompt();
      await deferredPrompt.userChoice;
      setDeferredPrompt(null);
      dismiss();
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
          Use {SITE_NAME} as an app
        </h2>
        <p className="mt-2 text-sm text-accent-ink/90 leading-relaxed max-w-xl">
          Add it to your home screen. Open it like a real app — no tabs, no
          noise.
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
