"use client";

import { useState, type FormEvent } from "react";

type FeedbackButtonProps = {
  pageUrl?: string;
  className?: string;
};

export function FeedbackButton({ pageUrl, className = "" }: FeedbackButtonProps) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">(
    "idle",
  );
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!message.trim()) return;

    setStatus("loading");
    setErrorMessage("");

    try {
      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: message.trim(),
          email: email.trim() || undefined,
          pageUrl: pageUrl ?? window.location.href,
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.error ?? "Failed to send feedback");
      }

      setStatus("success");
      setMessage("");
      setEmail("");
    } catch (error) {
      setStatus("error");
      setErrorMessage(
        error instanceof Error ? error.message : "Failed to send feedback",
      );
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`hover:text-accent underline-offset-2 hover:underline ${className}`}
      >
        Feedback
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-ink/40 p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-lg bg-paper p-6 shadow-lg border border-border"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 className="font-serif text-lg font-bold text-ink mb-4">
              Send feedback
            </h2>

            {status === "success" ? (
              <p className="font-sans text-sm text-muted mb-4">
                Thank you — your feedback was sent.
              </p>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label
                    htmlFor="feedback-message"
                    className="block text-sm font-sans text-ink mb-1"
                  >
                    Message
                  </label>
                  <textarea
                    id="feedback-message"
                    required
                    rows={4}
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                    className="w-full rounded-md border border-border bg-paper px-3 py-2 text-sm font-sans text-ink"
                  />
                </div>
                <div>
                  <label
                    htmlFor="feedback-email"
                    className="block text-sm font-sans text-ink mb-1"
                  >
                    Email (optional)
                  </label>
                  <input
                    id="feedback-email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="w-full rounded-md border border-border bg-paper px-3 py-2 text-sm font-sans text-ink"
                  />
                </div>
                {status === "error" && (
                  <p className="text-sm text-accent font-sans">{errorMessage}</p>
                )}
                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={status === "loading"}
                    className="rounded-md bg-accent px-4 py-2 text-sm font-sans text-paper disabled:opacity-60"
                  >
                    {status === "loading" ? "Sending…" : "Send"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setOpen(false)}
                    className="rounded-md px-4 py-2 text-sm font-sans text-muted hover:text-ink"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}

            {status === "success" && (
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  setStatus("idle");
                }}
                className="mt-2 rounded-md px-4 py-2 text-sm font-sans text-muted hover:text-ink"
              >
                Close
              </button>
            )}
          </div>
        </div>
      )}
    </>
  );
}
