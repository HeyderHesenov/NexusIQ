/** Paylaşılan tiplər — backend sxemləri ilə uyğunlaşır (Addım 2+). */

export type Category = "forex" | "us" | "crypto" | "commodities";

export interface NewsItem {
  id: string;
  title: string;
  summary: string | null;
  content?: string | null;
  imageUrl: string | null;
  category: Category;
  source: string | null;
  originalUrl: string | null;
  publishedAt: string; // ISO
  sentiment?: number | null;
  impactScore?: number | null;
  isProcessed?: boolean;
  translations?: Record<string, { title: string; body: string }> | null;
}

export type Impact = "up" | "down" | "mixed" | "neutral";

export interface ForecastPair {
  sym: string;
  impact: Impact;
  reason: string;
}

export interface Forecast {
  ready: boolean;
  summary?: string;
  pairs?: ForecastPair[];
}

export interface FearGreed {
  value: number;
  label: string;
  updatedAt: number;
}

export interface CalEvent {
  title: string;
  country: string;
  date: string;
  time: string;
  impact: string;
  forecast: string;
  previous: string;
}

export interface Earning {
  sym: string;
  name: string;
  date: string; // ISO YYYY-MM-DD
  time: string;
  ai: boolean;
}

export interface CryptoUnlock {
  sym: string;
  sector: "major" | "perp" | "rwa" | "ai";
  date: string; // ISO YYYY-MM-DD
  tokens: string;
  category: string;
}

export interface Quote {
  sym: string;
  val: string;
  chg: string;
  up: boolean;
  spark?: number[];
}

export interface MajorEvent {
  sym: string;
  date: string; // ISO YYYY-MM-DD
  type: "halving" | "escrow" | "burn" | "unlock";
  note: string;
}

export interface CorrAsset {
  key: string;
  label: string;
  sym: string;
}

export interface CorrMatrix {
  window: number;
  assets: CorrAsset[];
  matrix: (number | null)[][];
}

export interface CorrPairPoint {
  date: string;
  a: number;
  b: number;
}

export interface CorrPair {
  a: { key: string; label: string };
  b: { key: string; label: string };
  window: number;
  value: number;
  series: CorrPairPoint[];
  explanation?: string;
}
