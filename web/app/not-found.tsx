export default function NotFound() {
  return (
    <div className="py-16 text-center font-sans">
      <h1 className="font-serif text-3xl font-bold text-ink">Page not found</h1>
      <p className="mt-3 text-muted">
        This story may have been removed or the link is incorrect.
      </p>
      <a href="/" className="mt-6 inline-block text-accent hover:underline">
        Back to Bytez
      </a>
    </div>
  );
}
