/** @type {import('next').NextConfig} */
// Server-only daxili backend URL — brauzer eyni-origin `/backend/*`-a gedir,
// bu rewrite isə onu backend-ə yönləndirir. QƏSDƏN NEXT_PUBLIC_API_BASE DEYİL:
// o artıq `/backend`-dir, deməli destination `/backend/:path*` olardı → sonsuz
// döngü. DİQQƏT: Next rewrite-ları BUILD zamanı "bişirir", ona görə bu dəyər
// build vaxtı oxunur (runtime dəyişikliyi təsir etmir → build-də təyin et).
const BACKEND_INTERNAL_URL =
  process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8001/api/v1";
const isProd = process.env.NODE_ENV === "production";

// Content-Security-Policy — inline tema skripti + Google GIS üçün. 'unsafe-eval'
// və ws:// yalnız Next dev HMR üçün lazımdır → prod-da atılır (real bir XSS sink
// olsa eval/websocket vektoru bağlı qalsın). http://localhost:* prod-da da qalır,
// çünki brauzer API-yə birbaşa localhost:8001-ə (NEXT_PUBLIC_API_BASE) müraciət edir.
//
// `'unsafe-inline'` (script-src) — QƏSDƏN saxlanılır. Bu, ölçülmüş qərardır:
//   • Hash-əsaslı CSP MÜMKÜN DEYİL: Next App Router hər səhifədə ~8 ədəd
//     `self.__next_f.push(...)` inline RSC skripti buraxır və onların məzmunu
//     səhifədən-səhifəyə, build-dən-build-ə dəyişir (render olunmuş HTML-də
//     sayıldı: 9 inline blok, 8-i Next-in özündən).
//   • Nonce YEGANƏ alternativdir, o isə middleware tələb edir → nonce hər sorğuda
//     yenidir, deməli 14 STATİK səhifə per-request dinamikə çevrilir (real perf
//     itkisi) + yeni middleware səthi.
//   • Qazanc isə ~sıfırdır: iki müstəqil audit XSS SƏTHİNİ SIFIR tapdı — yeganə
//     `dangerouslySetInnerHTML` aşağıdakı statik tema skriptidir (interpolasiya
//     yoxdur), qalan hər şey React-escape olunur, markdown/HTML renderer yoxdur.
//     Üstəlik `'unsafe-inline'` yalnız INLINE inyeksiyaya imkan verir; xarici
//     skript (`<script src=//evil>`) `'self'` ilə onsuz da bloklanır.
// Yəni burada CSP əsas nəzarət deyil, müdafiə dərinliyidir və onun üçün 14
// səhifəni dinamikləşdirmək səmərəsiz mübadilədir.
//
// PLANLANAN sərtləşmə (auth işi, /backend marshrutu ilə PULSUZ gəlir): brauzer
// API-yə same-origin `/backend/*` üzərindən getdikdə `connect-src`-dən
// `http://localhost:*` və `https://www.googleapis.com` ÇIXIR (Google userinfo
// çağırışı server tərəfə keçir), `img-src` isə `'self'`-ə daralır.
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
  // http://localhost:* → backend thumbnail proksisi (/img/news/{id}); connect-src
  // ilə eyni səbəb. https: → id-siz Yahoo ehtiyat xəbərləri birbaşa naşirdən.
  "img-src 'self' data: https: http://localhost:*",
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
    // Eyni-origin proksi: brauzer `/backend/*` → backend (cookie/CSRF/Origin düzgün).
    return [
      {
        source: "/backend/:path*",
        destination: `${BACKEND_INTERNAL_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;
