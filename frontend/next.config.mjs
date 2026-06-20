/** @type {import('next').NextConfig} */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  images: {
    // Xəbər şəkilləri xarici mənbələrdən gəlir — istənilən hosta icazə.
    remotePatterns: [{ protocol: "https", hostname: "**" }],
  },
  async rewrites() {
    // Frontend /api/* → backend (CORS-suz lokal proxy).
    return [{ source: "/backend/:path*", destination: `${API_BASE}/:path*` }];
  },
};

export default nextConfig;
