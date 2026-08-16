import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Inter, Lora } from "next/font/google";
import { SerwistProvider } from "@serwist/next/react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { MobileTabBar } from "@/components/MobileTabBar";
import { InstallBanner } from "@/components/InstallBanner";
import { AllReadEgg } from "@/components/AllReadEgg";
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
    default: `${SITE_NAME} — Your TN signal`,
    template: `%s | ${SITE_NAME}`,
  },
  description:
    "TNforME gives you one clear story on what actually affects your life in Tamil Nadu — not every headline.",
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
          <SiteHeader />
          <InstallBanner />
          <main className="mx-auto max-w-5xl px-4 py-8 pb-tab-bar">{children}</main>
          <SiteFooter />
          <MobileTabBar />
          <AllReadEgg />
        </SerwistProvider>
      </body>
    </html>
  );
}
