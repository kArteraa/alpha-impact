import type { InterpretResponse, Role } from "../../src";
import { CACHE_TTL_MS } from "../config";

export const CACHE_KEY = "cache";

interface CacheEntry {
  response: InterpretResponse;
  storedAt: number;
}

export type CacheEntries = Record<string, CacheEntry>;

export function cacheKey(userId: string, clientId: string, role: Role, url: string): string {
  return JSON.stringify([userId, clientId, role, url]);
}

function fresh(entry: CacheEntry, now: number): boolean {
  return now - entry.storedAt < CACHE_TTL_MS;
}

export function readCached(entries: CacheEntries, key: string, now: number): InterpretResponse | undefined {
  const entry = entries[key];
  return entry !== undefined && fresh(entry, now) ? entry.response : undefined;
}

export function writeCached(
  entries: CacheEntries,
  key: string,
  response: InterpretResponse,
  now: number,
): CacheEntries {
  const kept = Object.entries(entries).filter(([, entry]) => fresh(entry, now));
  return { ...Object.fromEntries(kept), [key]: { response, storedAt: now } };
}
