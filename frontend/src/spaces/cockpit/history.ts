import { api } from '@/api/client'
import type { HistoryPoint } from '@/api/types'

const cache = new Map<string, { at: number; points: Promise<HistoryPoint[]> }>()
const TTL = 60_000

/** Historique (RRD Proxmox) mis en cache 60 s : plusieurs tuiles peuvent le partager. */
export function history(connectorId: string, resource: string, timeframe = 'hour'): Promise<HistoryPoint[]> {
  const key = `${connectorId}|${resource}|${timeframe}`
  const hit = cache.get(key)
  if (hit && Date.now() - hit.at < TTL) return hit.points
  const q = new URLSearchParams({ resource, timeframe })
  const points = api<{ points: HistoryPoint[] }>(`/api/v1/connectors/${connectorId}/history?${q}`).then((r) => r.points)
  cache.set(key, { at: Date.now(), points })
  points.catch(() => cache.delete(key))
  return points
}
