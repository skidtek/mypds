import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { api } from '@/api/client'
import type { Branding, Preferences } from '@/api/types'
import { setLocale, t, tk } from '@/i18n'

export const DEFAULT_PREFS: Preferences = {
  background: 'nature',
  color_mode: 'auto',
  accent: '#0A84FF',
  blur: 24,
  transparency: 55,
  search_engine: 'google',
  search_custom_url: null,
  search_autofocus: true,
  temperature_unit: 'celsius',
  wallpaper_light: null,
  wallpaper_dark: null,
  locale: 'auto',
}

export type WallpaperVariant = 'light' | 'dark'

export function wallpaperUrl(p: Preferences, variant: WallpaperVariant): string | null {
  const v = variant === 'light' ? p.wallpaper_light : p.wallpaper_dark
  return v ? `/api/v1/me/wallpaper/${variant}?v=${v}` : null
}

export const DEFAULT_BRANDING: Branding = {
  title: 'My Personal Digital Space',
  short_title: 'My Digital Space',
  subtitle: tk('Votre espace personnel'),
  display: 'full',
  show_logo: true,
  logo_position: 'top',
  logo_version: null,
}

export function logoUrl(b: Branding): string {
  return b.logo_version ? `/api/v1/branding/logo?v=${b.logo_version}` : '/logo.svg'
}

/** Titre de l'onglet et icône du navigateur suivent la marque. */
function applyBranding(b: Branding) {
  document.title = b.display === 'hidden' ? t('Accueil') : b.title
  const icon = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
  if (icon) {
    icon.href = logoUrl(b)
    icon.type = b.logo_version ? '' : 'image/svg+xml'
  }
}

const darkQuery = typeof window !== 'undefined' ? window.matchMedia('(prefers-color-scheme: dark)') : null

/** Applique les variables visuelles : les composants ne changent jamais, seules les variables. */
export function applyTheme(p: Preferences) {
  setLocale(p.locale ?? 'auto')
  const root = document.documentElement
  const dark = p.color_mode === 'dark' || (p.color_mode === 'auto' && !!darkQuery?.matches)
  const hasCustom = !!(p.wallpaper_light || p.wallpaper_dark)
  root.dataset.bg = p.background === 'custom' && !hasCustom ? 'nature' : p.background
  root.dataset.mode = dark ? 'dark' : 'light'
  const alpha = p.transparency / 100
  root.style.setProperty('--surface-alpha', alpha.toFixed(2))
  root.style.setProperty('--blur', `${p.blur}px`)
  root.style.setProperty('--accent', p.accent)
  // Fond personnel : celui du mode courant, sinon l'autre (assombri en mode sombre par le voile du thème)
  const wall = dark
    ? (wallpaperUrl(p, 'dark') ?? wallpaperUrl(p, 'light'))
    : (wallpaperUrl(p, 'light') ?? wallpaperUrl(p, 'dark'))
  if (wall) root.style.setProperty('--wallpaper', `url("${wall}")`)
  else root.style.removeProperty('--wallpaper')
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#141a3a' : '#aebbe3')
}

export const usePreferences = defineStore('preferences', () => {
  const prefs = ref<Preferences>({ ...DEFAULT_PREFS })
  const branding = ref<Branding>({ ...DEFAULT_BRANDING })
  let saveTimer: number | undefined

  async function load() {
    prefs.value = { ...DEFAULT_PREFS, ...(await api<Preferences>('/api/v1/me/preferences')) }
  }

  async function loadBranding() {
    try {
      branding.value = await api<Branding>('/api/v1/branding')
    } catch {
      branding.value = { ...DEFAULT_BRANDING }
    }
    applyBranding(branding.value)
  }

  /** Met à jour localement tout de suite, enregistre après un court délai. */
  function update(patch: Partial<Preferences>) {
    prefs.value = { ...prefs.value, ...patch }
    window.clearTimeout(saveTimer)
    saveTimer = window.setTimeout(() => {
      void api<Preferences>('/api/v1/me/preferences', { method: 'PUT', json: prefs.value })
    }, 500)
  }

  async function uploadWallpaper(variant: WallpaperVariant, file: File) {
    const body = new FormData()
    body.append('file', file)
    prefs.value = { ...DEFAULT_PREFS, ...(await api<Preferences>(`/api/v1/me/wallpaper/${variant}`, { method: 'PUT', body })) }
  }

  async function removeWallpaper(variant: WallpaperVariant) {
    prefs.value = { ...DEFAULT_PREFS, ...(await api<Preferences>(`/api/v1/me/wallpaper/${variant}`, { method: 'DELETE' })) }
  }

  async function saveBranding(b: Branding) {
    branding.value = await api<Branding>('/api/v1/branding', { method: 'PUT', json: b })
    applyBranding(branding.value)
  }

  async function uploadLogo(file: File) {
    const body = new FormData()
    body.append('file', file)
    branding.value = await api<Branding>('/api/v1/branding/logo', { method: 'PUT', body })
    applyBranding(branding.value)
  }

  async function resetLogo() {
    branding.value = await api<Branding>('/api/v1/branding/logo', { method: 'DELETE' })
    applyBranding(branding.value)
  }

  watch(prefs, (p) => applyTheme(p), { deep: true, immediate: true })
  darkQuery?.addEventListener('change', () => applyTheme(prefs.value))

  return { prefs, branding, load, loadBranding, update, saveBranding, uploadLogo, resetLogo, uploadWallpaper, removeWallpaper }
})
