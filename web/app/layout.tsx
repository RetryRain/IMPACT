import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Inter, Lora } from "next/font/google";
import { SerwistProvider } from "@serwist/next/react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { SITE_NAME, absoluteUrl } from "@/lib/site";
import "./globals.css";

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const serif = Lora({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: {
    default: `${SITE_NAME} — News for Tamil Nadu`,
    template: `%s | ${SITE_NAME}`,
  },
  description:
    "Bytez publishes events that matter to people in Tamil Nadu, synthesized from multiple trusted sources.",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: SITE_NAME,
  },
  openGraph: {
    siteName: SITE_NAME,
    type: "website",
    locale: "en_IN",
    url: absoluteUrl("/"),
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={`${sans.variable} ${serif.variable}`}
      suppressHydrationWarning
    >
      <body
        className="min-h-screen bg-paper text-ink font-sans antialiased"
        suppressHydrationWarning
      >
        <SerwistProvider swUrl="/sw.js">
          <SiteHeader />
          <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
          <SiteFooter />
        </SerwistProvider>
      </body>
    </html>
  );
}
