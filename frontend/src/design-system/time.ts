import { intlLocale, t } from '@/i18n'

/** « 12 min », « 3 h », « 2 j » — format compact de la maquette. */
export function ago(iso: string, now = Date.now()): string {
  const s = Math.max(0, (now - new Date(iso).getTime()) / 1000)
  if (s < 60) return t("à l'instant")
  if (s < 3600) return t('{n} min', { n: Math.floor(s / 60) })
  if (s < 86400) return t('{n} h', { n: Math.floor(s / 3600) })
  if (s < 86400 * 7) return t('{n} j', { n: Math.floor(s / 86400) })
  return new Date(iso).toLocaleDateString(intlLocale.value, { day: 'numeric', month: 'short' })
}

export function hhmm(iso: string): string {
  return new Date(iso).toLocaleTimeString(intlLocale.value, { hour: '2-digit', minute: '2-digit' })
}

export function syncedLabel(iso: string | null | undefined): string {
  return iso ? t('Mis à jour à {time}', { time: hhmm(iso) }) : t('Jamais synchronisé')
}

/** « il y a 12 min », « à l'instant » ou « le 3 nov. ». */
export function since(iso: string): string {
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 60) return t("à l'instant")
  if (s < 86400 * 7) return t('il y a {ago}', { ago: ago(iso) })
  return t('le {date}', { date: ago(iso) })
}
