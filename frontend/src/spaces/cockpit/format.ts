import { locale, t } from '@/i18n'

export function bytes(n: number | null | undefined): string {
  if (n == null) return '—'
  const units = locale.value === 'fr' ? ['o', 'Ko', 'Mo', 'Go', 'To', 'Po'] : ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  let v = n
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v >= 100 || i === 0 ? Math.round(v) : v.toFixed(1).replace('.', locale.value === 'fr' ? ',' : '.')} ${units[i]}`
}

export function pct(v: number | null | undefined): string {
  return v == null ? '—' : `${Math.round(v * 100)} %`
}

export function uptime(s: number | null | undefined): string {
  if (!s) return '—'
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  return d ? t('{d} j {h} h', { d, h }) : t('{h} h {m} min', { h, m: Math.floor((s % 3600) / 60) })
}

export function ratio(used: number | null | undefined, total: number | null | undefined): number | null {
  return used != null && total ? used / total : null
}

/** Niveau d'alerte d'une jauge : vert < 75 %, orange < 90 %, rouge au-delà. */
export function level(v: number | null | undefined): 'ok' | 'warn' | 'down' | 'unknown' {
  if (v == null) return 'unknown'
  return v < 0.75 ? 'ok' : v < 0.9 ? 'warn' : 'down'
}

/** Débit en bits par seconde : « 38,2 Mb/s » (« Mbit/s » en anglais). */
export function bitrate(bps: number | null | undefined): string {
  if (bps == null) return '—'
  const units = locale.value === 'fr' ? ['b/s', 'kb/s', 'Mb/s', 'Gb/s'] : ['bit/s', 'kbit/s', 'Mbit/s', 'Gbit/s']
  let v = bps
  let i = 0
  while (v >= 1000 && i < units.length - 1) {
    v /= 1000
    i++
  }
  return `${v >= 100 || i === 0 ? Math.round(v) : v.toFixed(1).replace('.', locale.value === 'fr' ? ',' : '.')} ${units[i]}`
}

/** Octets en unités décimales (capacités de disques et volumes, comme DSM). */
export function bytesDec(n: number | null | undefined): string {
  if (n == null) return '—'
  const units = locale.value === 'fr' ? ['o', 'Ko', 'Mo', 'Go', 'To', 'Po'] : ['B', 'kB', 'MB', 'GB', 'TB', 'PB']
  let v = n
  let i = 0
  while (v >= 1000 && i < units.length - 1) {
    v /= 1000
    i++
  }
  return `${v >= 100 || i === 0 ? Math.round(v) : v.toFixed(1).replace('.', locale.value === 'fr' ? ',' : '.')} ${units[i]}`
}
