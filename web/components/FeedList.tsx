import { FeedCard } from "./FeedCard";
import { FeedScrollRestore } from "./FeedScrollRestore";
import type { Story } from "@/lib/schema";

export function FeedList({ stories }: { stories: Story[] }) {
  if (stories.length === 0) {
    return (
      <p className="font-sans text-muted py-12 text-center">
        No stories yet. Check back after the next synthesis run.
      </p>
    );
  }

  return (
    <FeedScrollRestore>
      <div>
        {stories.map((story) => (
          <FeedCard key={story.id} story={story} />
        ))}
      </div>
    </FeedScrollRestore>
  );
}
