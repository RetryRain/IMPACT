import { FeedCard } from "./FeedCard";
import type { Story } from "@/lib/schema";

export function RelatedStories({ stories }: { stories: Story[] }) {
  if (stories.length === 0) return null;

  return (
    <section className="mt-12 border-t border-border pt-8">
      <h2 className="font-serif text-xl font-bold text-ink mb-4">Related</h2>
      <div>
        {stories.map((story) => (
          <FeedCard key={story.id} story={story} />
        ))}
      </div>
    </section>
  );
}
