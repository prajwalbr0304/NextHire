/** @type {import('next').NextConfig} */
const API = process.env.API_BASE || "http://127.0.0.1:8000";

const nextConfig = {
  async rewrites() {
    // proxy API calls to the FastAPI backend (same-origin from the browser)
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};

export default nextConfig;
