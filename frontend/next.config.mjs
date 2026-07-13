/** @type {import('next').NextConfig} */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8001";
const isProd = process.env.NODE_ENV === "production";

// Content-Security-Policy — inline tema skripti + Google GIS üçün. 'unsafe-eval'
// və ws:// yalnız Next dev HMR üçün lazımdır → prod-da atılır (real bir XSS sink
// olsa eval/websocket vektoru bağlı qalsın). http://localhost:* prod-da da qalır,
// çünki brauzer API-yə birbaşa localhost:8001-ə (NEXT_PUBLIC_API_BASE) müraciət edir.
const CSP = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'self'",
  "form-action 'self'",
  isProd
    ? "script-src 'self' 'unsafe-inline' https://accounts.google.com"
    : "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: https:",
  "font-src 'self' data:",
  isProd
    ? "connect-src 'self' http://localhost:* https://www.googleapis.com https://accounts.google.com"
    : "connect-src 'self' http://localhost:* ws://localhost:* https://www.googleapis.com https://accounts.google.com",
  "frame-src https://accounts.google.com",
].join("; ");

const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: CSP },
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig = {
  reactStrictMode: true,
  images: {
    // Xəbər şəkilləri birbaşa <img> ilə göstərilir (NewsImage), next/image
    // OPTIMIZER-i heç istifadə olunmur. Wildcard remotePatterns /_next/image-i
    // açıq proksiyə (SSRF: attacker-supplied host) çevirirdi — bağlandı.
    unoptimized: true,
    remotePatterns: [],
  },
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
  async rewrites() {
    // Frontend /api/* → backend (CORS-suz lokal proxy).
    return [{ source: "/backend/:path*", destination: `${API_BASE}/:path*` }];
  },
};

export default nextConfig;
