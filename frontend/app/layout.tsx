import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Sidebar, MobileNav } from "@/components/sidebar";

export const metadata: Metadata = {
  title: "Football Intelligence — Analytics Platform",
  description: "League standings, team form, matches and head-to-head from tested dbt marts.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#070B12",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="mx-auto w-full min-w-0 max-w-[1200px] flex-1 px-3 pb-28 pt-5 sm:px-6 lg:px-8 lg:pb-12 lg:pt-6">
              {children}
            </main>
          </div>
          <MobileNav />
        </Providers>
      </body>
    </html>
  );
}
