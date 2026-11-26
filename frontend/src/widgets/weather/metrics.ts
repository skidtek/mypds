/**
 * Indicateurs de la tuile météo (fonctions pures, testées) : position du soleil, pluie attendue,
 * niveaux de qualité de l'air et d'UV.
 */
import type { WeatherReport } from '@/api/types'
import { tk } from '@/i18n'

const minutes = (hhmm: string) => {
  const [h, m] = hhmm.split(':').map(Number)
  return (h ?? 0) * 60 + (m ?? 0)
}

/** Heure locale *du lieu* (et non du navigateur), en minutes depuis minuit. */
export function localMinutes(report: WeatherReport, nowMs = Date.now()): number {
  const d = new Date(nowMs + report.utc_offset_seconds * 1000)
  return d.getUTCHours() * 60 + d.getUTCMinutes()
}

/** 0 au lever, 1 au coucher, hors [0, 1] la nuit. */
export function sunProgress(report: WeatherReport, nowMs = Date.now()): number {
  const today = report.days[0]
  if (!today?.sunrise || !today.sunset) return report.current.is_day ? 0.5 : -1
  const rise = minutes(today.sunrise)
  const set = minutes(today.sunset)
  if (set <= rise) return report.current.is_day ? 0.5 : -1
  return (localMinutes(report, nowMs) - rise) / (set - rise)
}

const WET = new Set(['rain', 'drizzle', 'showers', 'thunderstorm', 'snow'])

/** Pluie (ou neige) en cours ou attendue aujourd'hui : on montre alors les précipitations au lieu du vent. */
export function rainExpected(report: WeatherReport): boolean {
  const today = report.days[0]
  return (
    WET.has(report.current.condition) ||
    (report.current.precipitation ?? 0) > 0 ||
    (today?.precipitation_probability ?? 0) >= 40 ||
    (today?.precipitation_sum ?? 0) >= 1
  )
}

export const AIR_LABELS: Record<'eu' | 'us', string[]> = {
  eu: [tk('Bon'), tk('Correct'), tk('Modéré'), tk('Mauvais'), tk('Très mauvais'), tk('Extrêmement mauvais')],
  us: [tk('Bon'), tk('Modéré'), tk('Mauvais pour les sensibles'), tk('Mauvais'), tk('Très mauvais'), tk('Dangereux')],
}
export const LEVEL_COLORS = ['#34c759', '#a3d84a', '#ffcc00', '#ff9500', '#ff3b30', '#af52de']

/** Indice UV : 0 faible, 1 modéré, 2 élevé, 3 très élevé, 4 extrême (échelle OMS). */
export function uvLevel(uv: number): number {
  return uv < 3 ? 0 : uv < 6 ? 1 : uv < 8 ? 2 : uv < 11 ? 3 : 4
}
export const UV_LABELS = [tk('Faible'), tk('Modéré'), tk('Élevé'), tk('Très élevé'), tk('Extrême')]
export const UV_COLORS = ['#34c759', '#ffcc00', '#ff9500', '#ff3b30', '#af52de']

/** Vent en km/h (Open-Meteo) ; converti en mph pour les utilisateurs en Fahrenheit. */
export function windValue(kmh: number, unit: 'celsius' | 'fahrenheit'): { value: number; unit: string } {
  return unit === 'fahrenheit' ? { value: Math.round(kmh / 1.609), unit: 'mph' } : { value: Math.round(kmh), unit: 'km/h' }
}

const DIRS = [tk('N'), tk('NE'), tk('E'), tk('SE'), tk('S'), tk('SO'), tk('O'), tk('NO')]
/** Direction d'où vient le vent, en 8 secteurs. */
export function windFrom(deg: number): string {
  return DIRS[Math.round((((deg % 360) + 360) % 360) / 45) % 8]!
}
