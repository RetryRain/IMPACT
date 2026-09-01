import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Inter, Lora } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import { SerwistProvider } from "@serwist/next/react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { MobileTabBar } from "@/components/MobileTabBar";
import {
  FeedReadProgressDesktopDock,
  FeedReadProgressProvider,
} from "@/components/FeedReadProgress";
import { InstallBanner } from "@/components/InstallBanner";
import { AllReadEgg } from "@/components/AllReadEgg";
import { SiteJsonLd } from "@/components/SiteJsonLd";
import { SITE_DESCRIPTION, SITE_NAME, SITE_TAGLINE, absoluteUrl } from "@/lib/site";
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
    default: `${SITE_NAME} | ${SITE_TAGLINE}`,
    template: `%s | ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/icons/icon.svg", type: "image/svg+xml" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: "/icons/apple-touch-icon.png",
  },
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
          <FeedReadProgressProvider>
            <SiteJsonLd />
            <SiteHeader />
            <InstallBanner />
            <main className="mx-auto max-w-5xl px-4 py-8 pb-tab-bar">{children}</main>
            <SiteFooter />
            <MobileTabBar />
            <FeedReadProgressDesktopDock />
            <AllReadEgg />
          </FeedReadProgressProvider>
        </SerwistProvider>
        <Analytics />
      </body>
    </html>
  );
}
