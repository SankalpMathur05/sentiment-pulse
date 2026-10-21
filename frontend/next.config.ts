import type { NextConfig } from "next";

// Where the FastAPI backend lives, as seen from the Next.js server (a Docker service
// name, or the Render URL on Vercel). The browser only ever calls same-origin paths
// and Next.js proxies them, so the API never needs CORS. Read at build time.
const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  reactCompiler: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_INTERNAL_URL}/api/:path*` },
      { source: "/health", destination: `${API_INTERNAL_URL}/health` },
    ];
  },
};

export default nextConfig;
