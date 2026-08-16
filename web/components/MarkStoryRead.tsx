"use client";

import { useEffect } from "react";
import { markStoryRead } from "@/lib/visited-store";

type MarkStoryReadProps = {
  id: string;
  slug: string;
};

export function MarkStoryRead({ id, slug }: MarkStoryReadProps) {
  useEffect(() => {
    markStoryRead(id, slug);
  }, [id, slug]);

  return null;
}
