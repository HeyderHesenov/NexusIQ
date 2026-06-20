/**
 * Tab üzrə təqvim kateqoriyaları — MarketCalendar dropdown-u bunları göstərir.
 * Hər kateqoriya: göstərmə növü (kind) + məlumatı çəkən load() + axtarış nümunəsi.
 */
import {
  getCalendar,
  getCommodities,
  getCryptoCalendar,
  getEarnings,
  getMajorsCalendar,
  getMetals,
} from "@/lib/api";
import type { Category } from "@/types";

export type CalKind =
  | "earnings"
  | "events"
  | "unlocks"
  | "prices"
  | "cryptoEvents";

export interface CalCategory {
  key: string;
  labelKey: string;
  kind: CalKind;
  load: () => Promise<unknown[]>;
  searchable?: boolean; // axtarış qutusu göstərilsin
  searchEx?: string; // placeholder nümunəsi (taba uyğun)
}

const US: CalCategory[] = [
  {
    key: "earnings",
    labelKey: "market.earnings",
    kind: "earnings",
    load: getEarnings,
    searchable: true,
    searchEx: "NVDA",
  },
  {
    key: "ai",
    labelKey: "market.aiStocks",
    kind: "earnings",
    load: () => getEarnings().then((d) => d.filter((e) => e.ai)),
    searchable: true,
    searchEx: "NVDA",
  },
  {
    key: "usd",
    labelKey: "market.usdEvents",
    kind: "events",
    load: () => getCalendar().then((d) => d.filter((e) => e.country === "USD")),
    searchable: true,
    searchEx: "CPI",
  },
];

const FOREX: CalCategory[] = [
  {
    key: "currencies",
    labelKey: "market.currencies",
    kind: "events",
    load: getCalendar,
    searchable: true,
    searchEx: "EUR/USD",
  },
  {
    key: "metals",
    labelKey: "market.metals",
    kind: "prices",
    load: getMetals,
    searchable: true,
    searchEx: "Gold",
  },
];

const CRYPTO: CalCategory[] = [
  {
    key: "major",
    labelKey: "market.majors",
    kind: "cryptoEvents",
    load: getMajorsCalendar,
    searchable: true,
    searchEx: "BTC/USD",
  },
  {
    key: "perp",
    labelKey: "market.perpDex",
    kind: "unlocks",
    load: () => getCryptoCalendar().then((d) => d.filter((u) => u.sector === "perp")),
    searchable: true,
    searchEx: "HYPE",
  },
  {
    key: "rwa",
    labelKey: "market.rwa",
    kind: "unlocks",
    load: () => getCryptoCalendar().then((d) => d.filter((u) => u.sector === "rwa")),
    searchable: true,
    searchEx: "ONDO",
  },
  {
    key: "ai",
    labelKey: "market.aiCoins",
    kind: "unlocks",
    load: () => getCryptoCalendar().then((d) => d.filter((u) => u.sector === "ai")),
    searchable: true,
    searchEx: "TAO",
  },
];

const COMMODITIES: CalCategory[] = [
  {
    key: "all",
    labelKey: "market.commodities",
    kind: "prices",
    load: getCommodities,
    searchable: true,
    searchEx: "Uranium",
  },
];

export const CATEGORIES: Record<Category, CalCategory[]> = {
  us: US,
  forex: FOREX,
  crypto: CRYPTO,
  commodities: COMMODITIES,
};
