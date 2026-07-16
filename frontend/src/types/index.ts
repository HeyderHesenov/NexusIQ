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

/** Proqnoz doğruluq nişanı (Faza C doldurur; Faza A-da həmişə null). */
export interface TrustBadge {
  hitRate: number;
  baseRate: number;
  delta: number;
  n: number;
  horizon: number;
}

/** "Mənə Aid" — bir izlənən aktivə toxunan xəbərlərin digesti. */
export interface AssetDigest {
  key: string;
  label: string;
  count: number;
  sinceCount: number; // sən yox ikən (son baxışdan bəri)
  sentimentTrend: number[]; // gün üzrə orta əhval (sparkline)
  news: NewsItem[];
  trust: TrustBadge | null;
}

/** Watchlist digest cavabı — aktiv üzrə qruplanmış. */
export interface WatchlistIntel {
  ready: boolean;
  sinceCount: number; // bütün aktivlər üzrə cəmi
  assets: AssetDigest[];
}

/** Portfel — mövqe + canlı qiymət + P&L (Faza B). */
export interface Position {
  key: string;
  label: string;
  qty: number;
  avgCost: number | null;
  price: number | null;
  chgPct: number | null; // gündəlik dəyişim (dürüst etiket)
  value: number | null;
  pnl: number | null;
  pnlPct: number | null;
  weight: number; // 0..1
}
export interface PortfolioTotals {
  value: number;
  cost: number;
  pnl: number | null;
  pnlPct: number | null;
}
/** Pul-çəkili xəbər — NewsItem + portfelə təsir sahələri. */
export interface PortfolioNews extends NewsItem {
  relevanceScore?: number;
  moneyTilt?: number; // müsbət = portfelə yüksəliş meyli
  touched?: string[];
}
export interface PortfolioIntel {
  ready: boolean;
  totals: PortfolioTotals;
  positions: Position[];
  news: PortfolioNews[];
}

/** Proqnoz doğruluq kartı — bir slice (Faza C). */
export interface AccuracySlice {
  key: string;
  label: string;
  horizon: number;
  n: number;
  hitRate: number; // 0..1
  baseRate: number; // naiv "həmişə ▲"
  delta: number; // hitRate − baseRate
  insufficient: boolean; // n<20 → "toplanır"
}
export interface AccuracyCard {
  ready: boolean;
  by: string;
  horizon: number;
  slices: AccuracySlice[];
}

/** Saxlanan bazar təqvim hadisəsi — kartın /brief normallaşmasından qurulur. */
export interface SavedEvent {
  id: string; // sabit törəmə açar
  name: string; // başlıq
  badge: string; // sym / ölkə
  sub: string; // tarix · meta sətri
  href: string; // /brief linki
  savedAt: number;
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

/** Tarixi Analoq motoru — bənzər keçmiş hadisə + aktivin sonrakı hərəkəti. */
export interface AnalogWindow {
  avg: number | null;
  hitRate: number | null;
  count: number;
}
export interface AnalogEvent {
  id: number;
  title: string;
  publishedAt: string;
  similarity: number;
  moves: Record<"1" | "5" | "30", number | null>;
}
export interface AnalogResult {
  ready: boolean;
  asset?: { key: string; label: string };
  count?: number;
  windows?: Record<"1" | "5" | "30", AnalogWindow>;
  events?: AnalogEvent[];
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
  actual?: string;
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

export type AssetType =
  | "crypto"
  | "index"
  | "forex"
  | "commodity"
  | "metal"
  | "stock"
  | "industrial";

export interface Asset {
  key: string;
  label: string;
  sym: string;
  type: AssetType;
}

export interface AssetQuote {
  key: string;
  label: string;
  type: AssetType;
  val: string;
  price: number;
  chg: string;
  chgPct: number;
  up: boolean;
}

export interface AssetHistory {
  key: string;
  label: string;
  type: AssetType;
  range: string;
  points: { date: string; close: number }[];
  changePct: number;
}

export interface AssetDetail {
  quote: AssetQuote | null;
  history: AssetHistory | null;
}

export interface AssetOverview {
  key: string;
  label: string;
  type: AssetType;
  val: string;
  price: number;
  chg: string;
  chgPct: number;
  up: boolean;
  spark: number[];
}

export type RadarCategory = "crypto" | "stock" | "commodity";

export interface RadarItem {
  key: string;
  label: string;
  name?: string;
  type: RadarCategory;
  val: string;
  price: number;
  chg: string;
  chgPct: number;
  up: boolean;
  spark: number[];
  score: number;
  breakdown: Record<string, number>;
  mcap: number;
  mcapFmt: string;
  link: string;
  // crypto
  revenue30d?: number;
  revenueFmt?: string;
  category?: string;
  // stock / commodity
  theme?: string;
}

export interface RadarDetail extends RadarItem {
  tab: RadarCategory;
  homepage?: string | null;
  github?: string | null;
  image?: string | null;
}

export type AnomalySeverity = "medium" | "high" | "extreme";

export interface Anomaly {
  key: string;
  label: string;
  type: AssetType;
  price_z: number;
  volume_z: number;
  change_pct: number;
  severity: AnomalySeverity;
  last: number;
  asof: string;
}

/** Müşahidə altında — həddi keçməyən, lakin normadan uzaqlaşan aktiv (severity yox). */
export type NearMove = Omit<Anomaly, "severity">;

/** /anomalies cavabı — anomaliyalar + müşahidə siyahısı + statistika. */
export interface AnomalyScan {
  asof: string;
  anomalies: Anomaly[];
  near: NearMove[];
  stats: { universe: number; anomalies: number; near: number };
}

export interface PowerLawProjection {
  years: number;
  date: string;
  model: number;
  support: number;
  resistance: number;
}

export interface PowerLawPoint {
  date: string;
  actual: number;
  model: number;
  low: number;
  high: number;
}

export interface PowerLaw {
  key?: string;
  label?: string;
  a: number;
  b: number;
  r2: number;
  genesis: string;
  lastDate: string;
  price: number;
  model: number;
  support: number;
  resistance: number;
  deviationPct: number;
  projections: PowerLawProjection[];
  series: PowerLawPoint[];
}
