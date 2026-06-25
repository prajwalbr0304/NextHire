import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nexthire — Candidate Intelligence",
  description: "Nexthire — AI candidate ranking",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans">{children}</body>
    </html>
  );
}
