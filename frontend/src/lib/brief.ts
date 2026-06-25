/** /brief səhifəsinə sorğu-parametrli link qurur (təqvim/hadisə kartları üçün). */
export function briefHref(params: Record<string, string>): string {
  return "/brief?" + new URLSearchParams(params).toString();
}
