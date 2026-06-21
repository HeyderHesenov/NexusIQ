import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "@/styles/globals.css";
import { AuthGate } from "@/components/auth/AuthGate";
import { LanguageProvider } from "@/lib/i18n";

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
    <html lang="az" className={`dark ${inter.variable} ${jetbrains.variable}`}>
      <body className="min-h-screen bg-bg text-text font-sans antialiased">
        <LanguageProvider>
          <AuthGate>{children}</AuthGate>
        </LanguageProvider>
      </body>
    </html>
  );
}
