import { paragraphize } from "@/lib/format";

export function ArticleBody({ body }: { body: string }) {
  const paragraphs = paragraphize(body);

  return (
    <div className="prose-article font-sans text-ink leading-relaxed space-y-4">
      {paragraphs.map((paragraph, index) => (
        <p key={index}>{paragraph}</p>
      ))}
    </div>
  );
}
