/**
 * Traduction de l'interface (français / anglais), sans dépendance.
 * Le texte français sert de clé : `t('Réglages')` renvoie « Settings » en anglais.
 * Paramètres : `t('{n} services', { n: 8 })`. Les textes absents du catalogue restent en français.
 */
import { computed, ref, type App } from 'vue'
import en from './en'

export type Locale = 'fr' | 'en'
export type LocalePref = 'auto' | Locale

function detect(): Locale {
  const langs = typeof navigator !== 'undefined' ? navigator.languages ?? [navigator.language] : []
  return langs.some((l) => l?.toLowerCase().startsWith('fr')) ? 'fr' : 'en'
}

export const locale = ref<Locale>(detect())
export const intlLocale = computed(() => (locale.value === 'fr' ? 'fr-FR' : 'en-GB'))

export function setLocale(pref: LocalePref) {
  locale.value = pref === 'auto' ? detect() : pref
  if (typeof document !== 'undefined') document.documentElement.lang = locale.value
}

const CATALOGS: Record<Locale, Record<string, string>> = { fr: {}, en }

export function t(key: string, params?: Record<string, string | number | null | undefined>): string {
  const msg = locale.value === 'fr' ? key : (CATALOGS[locale.value][key] ?? key)
  if (!params) return msg
  return msg.replace(/\{(\w+)\}/g, (m, k: string) => (params[k] == null ? m : String(params[k])))
}

/** Pluriel simple : `tn(n, '{n} service', '{n} services')`. */
export function tn(n: number, one: string, many: string, params: Record<string, string | number> = {}): string {
  return t(n > 1 || n === 0 && locale.value === 'en' ? many : one, { n, ...params })
}

export const i18n = {
  install(app: App) {
    app.config.globalProperties.$t = t
    app.config.globalProperties.$tn = tn
  },
}

declare module 'vue' {
  interface ComponentCustomProperties {
    $t: typeof t
    $tn: typeof tn
  }
}

/** Marque un texte à traduire plus tard (listes constantes) : renvoie la clé telle quelle. */
export const tk = (key: string) => key
