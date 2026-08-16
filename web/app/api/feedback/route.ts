import { NextResponse } from "next/server";
import { feedback } from "@/lib/feedback-schema";
import {
  getFeedbackDb,
  isFeedbackDatabaseConfigured,
} from "@/lib/feedback-db";

type FeedbackPayload = {
  message?: string;
  email?: string;
  pageUrl?: string;
};

export async function POST(request: Request) {
  if (!isFeedbackDatabaseConfigured()) {
    return NextResponse.json(
      {
        error:
          "Feedback is not configured. Set FEEDBACK_DATABASE_URL in the environment.",
      },
      { status: 503 },
    );
  }

  let payload: FeedbackPayload;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const message = payload.message?.trim();
  if (!message) {
    return NextResponse.json({ error: "Message is required" }, { status: 400 });
  }

  const email = payload.email?.trim() || null;
  const pageUrl = payload.pageUrl?.trim() || null;
  const userAgent = request.headers.get("user-agent") ?? null;

  const db = getFeedbackDb();
  await db.insert(feedback).values({
    message,
    email,
    pageUrl,
    userAgent,
  });

  return NextResponse.json({ ok: true });
}
