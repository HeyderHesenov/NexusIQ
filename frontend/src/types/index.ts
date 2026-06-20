/** Paylaşılan tiplər — backend sxemləri ilə uyğunlaşır (Addım 2+). */

export type Category = "forex" | "us" | "crypto";

export interface NewsItem {
  id: string;
  title: string;
  summary: string | null;
  imageUrl: string | null;
  category: Category;
  source: string | null;
  originalUrl: string | null;
  publishedAt: string; // ISO
  sentiment?: number | null;
  impactScore?: number | null;
}
