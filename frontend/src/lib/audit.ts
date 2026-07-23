/**
 * Təhlükəsizlik "son fəaliyyət" jurnalı — yalnız oxunur.
 *
 * `/me/audit` izlənən `/me/*` namespace-dədir → ümumi `apiGet` (401→refresh dedup)
 * işlədilir, `authRequest` YOX.
 */
import { apiGet } from "./api";

export interface AuditEvent {
  id: string;
  event: string;
  ip: string | null;
  userAgent: string | null;
  meta: Record<string, unknown> | null;
  createdAt: string | null;
}

/** İstifadəçinin öz son təhlükəsizlik hadisələri (ən son 50). */
export function listAudit(): Promise<AuditEvent[]> {
  return apiGet<AuditEvent[]>("/me/audit");
}
