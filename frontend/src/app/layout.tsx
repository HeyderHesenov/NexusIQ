import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "@/styles/globals.css";
import { AuthGate } from "@/components/auth/AuthGate";
import { AuthProvider } from "@/lib/auth-context";
import { LanguageProvider } from "@/lib/i18n";
import { ThemeProvider } from "@/lib/theme";
import { AlertWatcher } from "@/components/alerts/AlertWatcher";
import { RoutePrewarm } from "@/components/layout/RoutePrewarm";
import { AuthedChrome } from "@/components/layout/AuthedChrome";
import { BackendStatusBanner } from "@/components/system/BackendStatusBanner";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "NexusIQ — Financial Intelligence",
  description: "AI-driven financial news, analysis and correlation terminal.",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, title: "NexusIQ", statusBarStyle: "black-translucent" },
  icons: { icon: "/icon.svg", apple: "/icon-192.png" },
  // Müasir standart (apple-mobile-web-app-capable deprekasiyasını əvəzləyir).
  other: { "mobile-web-app-capable": "yes" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0a0a0b",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="az"
      suppressHydrationWarning
      className={`dark ${inter.variable} ${jetbrains.variable}`}
    >
      <head>
        {/* Tema flash-ın qarşısını al — paint-dən əvvəl class qoy. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('nexusiq_theme');if(t!=='light'&&t!=='dark')t='dark';var e=document.documentElement;e.classList.remove('dark','light');e.classList.add(t);}catch(e){}})();`,
          }}
        />
      </head>
      <body className="min-h-screen bg-bg text-text font-sans antialiased">
        <ThemeProvider>
          <LanguageProvider>
            <AuthProvider>
              <AuthGate>{children}</AuthGate>
              {/* Yalnız authed chrome — publik marşrutlarda (/reset) görünmür */}
              <AuthedChrome />
              <AlertWatcher />
              <RoutePrewarm />
              <BackendStatusBanner />
            </AuthProvider>
          </LanguageProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
