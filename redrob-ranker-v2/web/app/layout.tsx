import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Council — Candidate Intelligence",
  description: "Council of Nine — AI candidate ranking",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans">{children}</body>
    </html>
  );
}
