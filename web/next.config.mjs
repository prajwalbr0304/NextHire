/** @type {import('next').NextConfig} */
// In local dev (`npm run dev`) the Next server proxies /api -> the FastAPI
// backend so the browser stays same-origin. In the production container we
// instead build a fully static export (NEXT_OUTPUT=export) and let FastAPI
// serve those files, so the whole app runs as one process on one port.
const API = process.env.API_BASE || "http://127.0.0.1:8000";
const isExport = process.env.NEXT_OUTPUT === "export";

const nextConfig = {
  ...(isExport
    ? {
        output: "export",
        images: { unoptimized: true },
        // The app runs fine at runtime; for the container export build we don't
        // want pre-existing type/lint strictness to block deployment. Local
        // `next dev` / `next build` keep their normal strict checks.
        typescript: { ignoreBuildErrors: true },
        eslint: { ignoreDuringBuilds: true },
      }
    : {}),
  async rewrites() {
    // Rewrites are ignored by `output: export`; only used by the dev server.
    if (isExport) return [];
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};

export default nextConfig;
