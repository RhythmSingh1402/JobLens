import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Job Match MVP",
  description: "Upload a resume, get ranked job matches.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900">
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
            <span className="text-lg font-semibold">Job Match</span>
            <nav className="flex gap-4 text-sm font-medium text-slate-600">
              <Link href="/upload" className="hover:text-slate-900">
                Upload
              </Link>
              <Link href="/matches" className="hover:text-slate-900">
                Matches
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-3xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
