import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";

export const metadata: Metadata = {
  title: "DataTales review (local)",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB">
      <body>
        <nav className="topbar" aria-label="Main">
          <Link href="/" className="brand">
            DataTales review
          </Link>
          <Link href="/findings">Findings</Link>
          <Link href="/stories">Stories</Link>
          <Link href="/datasets">Datasets &amp; jobs</Link>
          <Link href="/recipes">Recipes</Link>
          <span className="local" title="Never deploy this app: it holds the service-role key.">
            LOCAL ONLY
          </span>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
