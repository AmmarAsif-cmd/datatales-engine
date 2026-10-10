import type { Metadata } from "next";
import Link from "next/link";

import { pageUser } from "@/lib/gate";

import "./globals.css";

export const metadata: Metadata = {
  title: "DataTales review",
  robots: { index: false, follow: false },
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const user = await pageUser();
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
          <span className="local" title="Protected by Cloudflare Access">
            {user?.local ? "LOCAL DEV" : "ADMIN"}
          </span>
          {user && <span className="user">{user.email}</span>}
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
