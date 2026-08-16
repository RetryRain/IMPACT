"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getReadStoryIds,
  markAllReadEggShown,
  wasAllReadEggShown,
} from "@/lib/visited-store";

const TOAST_MS = 4500;

const MESSAGE =
  "That's all of it. Congratulations — you now have enough signal to survive until we update. Go touch grass. Or a filter coffee.";

function buildSetKey(ids: string[]): string {
  return [...ids].sort().join(",");
}

export function AllReadEgg() {
  const [show, setShow] = useState(false);
  const checking = useRef(false);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const checkAllRead = useCallback(async () => {
    if (checking.current) return;
    checking.current = true;
    try {
      const response = await fetch("/api/stories/ids");
      if (!response.ok) return;
      const data = (await response.json()) as { ids?: string[] };
      const allIds = data.ids ?? [];
      if (allIds.length === 0) return;

      const readIds = await getReadStoryIds();
      const readSet = new Set(readIds);
      const allRead = allIds.every((id) => readSet.has(id));
      if (!allRead) return;

      const setKey = buildSetKey(allIds);
      if (await wasAllReadEggShown(setKey)) return;

      await markAllReadEggShown(setKey);
      setShow(true);
      if (hideTimer.current) clearTimeout(hideTimer.current);
      hideTimer.current = setTimeout(() => setShow(false), TOAST_MS);
    } catch {
      // ignore network / IDB errors
    } finally {
      checking.current = false;
    }
  }, []);

  useEffect(() => {
    checkAllRead();
    const onStoryRead = () => checkAllRead();
    window.addEventListener("tnforme:story-read", onStoryRead);
    return () => {
      window.removeEventListener("tnforme:story-read", onStoryRead);
      if (hideTimer.current) clearTimeout(hideTimer.current);
    };
  }, [checkAllRead]);

  if (!show) return null;

  return (
    <div
      className="fixed bottom-6 left-4 right-4 z-[90] mx-auto max-w-md"
      role="status"
      aria-live="polite"
    >
      <div className="rounded-xl bg-accent px-4 py-3 text-sm font-sans text-paper leading-relaxed shadow-lg">
        {MESSAGE}
      </div>
    </div>
  );
}
