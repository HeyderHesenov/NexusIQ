import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Tailwind siniflərini təhlükəsiz birləşdirir. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
