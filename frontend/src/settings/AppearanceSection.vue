<script setup lang="ts">
import { PhImage, PhMoon, PhSun, PhTrash, PhUploadSimple } from '@phosphor-icons/vue'
import { reactive, ref } from 'vue'
import type { BackgroundName } from '@/api/types'
import { usePreferences, wallpaperUrl, type WallpaperVariant } from '@/stores/preferences'
import { t, tk } from '@/i18n'

const store = usePreferences()
const MAX = 8 * 1024 * 1024
const inputs = reactive<Record<WallpaperVariant, HTMLInputElement | null>>({ light: null, dark: null })
const busy = ref<WallpaperVariant | null>(null)
const wallError = ref('')
const SLOTS: { id: WallpaperVariant; label: string; icon: typeof PhSun }[] = [
  { id: 'light', label: tk('Mode clair'), icon: PhSun },
  { id: 'dark', label: tk('Mode sombre'), icon: PhMoon },
]

async function onWallpaper(variant: WallpaperVariant, e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  wallError.value = ''
  if (file.size > MAX) {
    wallError.value = t('Image trop volumineuse (8 Mo maximum).')
    return
  }
  busy.value = variant
  try {
    await store.uploadWallpaper(variant, file)
  } catch (err) {
    wallError.value = err instanceof Error ? err.message : String(err)
  } finally {
    busy.value = null
  }
}

async function removeWallpaper(variant: WallpaperVariant) {
  wallError.value = ''
  try {
    await store.removeWallpaper(variant)
  } catch (err) {
    wallError.value = err instanceof Error ? err.message : String(err)
  }
}
const BACKGROUNDS: { id: Exclude<BackgroundName, 'custom'>; name: string }[] = [
  { id: 'nature', name: tk('Nature') },
  { id: 'abstract', name: tk('Abstrait') },
  { id: 'minimal', name: tk('Minimaliste') },
  { id: 'it', name: 'IT' },
]
const hasCustom = () => !!(store.prefs.wallpaper_light || store.prefs.wallpaper_dark)
// Fond personnel : sans image dédiée, une variante reprend celle de l'autre mode
const customHalf = (variant: WallpaperVariant) =>
  wallpaperUrl(store.prefs, variant) ?? wallpaperUrl(store.prefs, variant === 'light' ? 'dark' : 'light')
const ACCENTS = ['#0A84FF', '#5E5CE6', '#BF5AF2', '#FF375F', '#FF9F0A', '#30D158', '#64D2FF', '#8E8E93']
</script>

<template>
  <section class="sec">
    <h2>{{ $t('Apparence') }}</h2>
    <p class="theme-line">
      <span class="faint">{{ $t('Thème :') }}</span> <strong>{{ $t('Glassmorphism') }}</strong>
      <span class="faint">{{ $t(' — surfaces de verre dépoli, réglables ci-dessous.') }}</span>
    </p>
    <div class="field">
      <span>{{ $t('Mode') }}</span>
      <div class="seg">
        <button type="button" :aria-pressed="store.prefs.color_mode === 'auto'" @click="store.update({ color_mode: 'auto' })">{{ $t('Automatique') }}</button>
        <button type="button" :aria-pressed="store.prefs.color_mode === 'light'" @click="store.update({ color_mode: 'light' })">{{ $t('Clair') }}</button>
        <button type="button" :aria-pressed="store.prefs.color_mode === 'dark'" @click="store.update({ color_mode: 'dark' })">{{ $t('Sombre') }}</button>
      </div>
      <p class="faint note">{{ $t('Automatique suit le réglage clair / sombre de l\'appareil. Chaque fond s\'adapte au mode.') }}</p>
    </div>
    <div class="field">
      <span>{{ $t('Fond d\'écran') }}</span>
      <div class="bgs" role="radiogroup" :aria-label="$t('Fond d\'écran')">
        <button
          v-for="b in BACKGROUNDS"
          :key="b.id"
          type="button"
          class="bg"
          role="radio"
          :aria-checked="store.prefs.background === b.id"
          @click="store.update({ background: b.id })"
        >
          <span class="split" aria-hidden="true">
            <span class="half" :class="`pv-${b.id}-light`"><PhSun :size="12" weight="fill" /></span>
            <span class="half" :class="`pv-${b.id}-dark`"><PhMoon :size="12" weight="fill" /></span>
          </span>
          <span>{{ $t(b.name) }}</span>
        </button>
        <button
          type="button"
          class="bg"
          role="radio"
          :aria-checked="store.prefs.background === 'custom'"
          :disabled="!hasCustom()"
          :title="hasCustom() ? undefined : $t('Importez d\'abord une image ci-dessous')"
          @click="store.update({ background: 'custom' })"
        >
          <span class="split" aria-hidden="true">
            <span v-for="v in (['light', 'dark'] as const)" :key="v" class="half custom-half" :class="{ empty: !customHalf(v) }">
              <img v-if="customHalf(v)" :src="customHalf(v)!" alt="" />
              <PhImage v-else :size="16" />
            </span>
          </span>
          <span>{{ $t('Personnel') }}</span>
        </button>
      </div>
    </div>
    <div class="field">
      <span>{{ $t('Couleur d\'accentuation') }}</span>
      <div class="accents">
        <button
          v-for="c in ACCENTS"
          :key="c"
          type="button"
          class="acc"
          :style="{ background: c }"
          :aria-pressed="store.prefs.accent.toUpperCase() === c"
          :aria-label="$t('Accent {name}', { name: c })"
          @click="store.update({ accent: c })"
        />
        <label class="acc custom" :title="$t('Couleur personnalisée')">
          <input type="color" :value="store.prefs.accent" :aria-label="$t('Couleur personnalisée')" @input="store.update({ accent: ($event.target as HTMLInputElement).value.toUpperCase() })" />
        </label>
      </div>
    </div>
    <label class="field">
      <span>{{ $t('Intensité du flou : {n} px', { n: store.prefs.blur }) }}</span>
      <input type="range" min="0" max="40" :value="store.prefs.blur" @input="store.update({ blur: +($event.target as HTMLInputElement).value })" />
    </label>
    <label class="field">
      <span>{{ $t('Opacité des surfaces : {n} %', { n: store.prefs.transparency }) }}</span>
      <input type="range" min="20" max="90" :value="store.prefs.transparency" @input="store.update({ transparency: +($event.target as HTMLInputElement).value })" />
    </label>
    <div class="field">
      <span>{{ $t('Vos images (fond « Personnel »)') }}</span>
      <div class="walls">
        <div v-for="slot in SLOTS" :key="slot.id" class="wall">
          <div class="wall-preview" :class="{ empty: !wallpaperUrl(store.prefs, slot.id) }">
            <img v-if="wallpaperUrl(store.prefs, slot.id)" :src="wallpaperUrl(store.prefs, slot.id)!" alt="" />
            <PhImage v-else :size="26" />
            <span class="wall-tag"><component :is="slot.icon" :size="13" weight="fill" /> {{ $t(slot.label) }}</span>
          </div>
          <div class="wall-actions">
            <button class="btn small" type="button" :disabled="busy !== null" @click="inputs[slot.id]?.click()">
              <PhUploadSimple :size="14" /> {{ busy === slot.id ? 'Import…' : wallpaperUrl(store.prefs, slot.id) ? 'Remplacer' : 'Importer' }}
            </button>
            <button v-if="wallpaperUrl(store.prefs, slot.id)" class="btn small" type="button" :aria-label="$t('Retirer le fond {name}', { name: $t(slot.label) })" @click="removeWallpaper(slot.id)">
              <PhTrash :size="14" />
            </button>
          </div>
          <input :ref="(el) => (inputs[slot.id] = el as HTMLInputElement)" type="file" accept="image/png,image/jpeg,image/webp" hidden @change="onWallpaper(slot.id, $event)" />
        </div>
      </div>
      <p class="faint note">
        {{ $t('PNG, JPEG ou WebP, 8 Mo maximum. Importer une image sélectionne le fond « Personnel ». Avec une seule image, elle sert dans les deux modes (légèrement assombrie en mode sombre). Vos images sont privées.') }}
      </p>
      <p v-if="wallError" class="error-text">{{ wallError }}</p>
    </div>
  </section>
</template>

<style scoped>
.theme-line {
  margin: 0;
  font-size: 14px;
}
.bgs {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(108px, 1fr));
  gap: 10px;
}
.bg {
  display: grid;
  gap: 8px;
  padding: 8px;
  border-radius: var(--radius-md);
  border: 2px solid transparent;
  background: rgb(var(--surface-rgb) / 0.5);
  font-size: 13.5px;
  font-weight: 600;
}
.bg[aria-checked='true'] {
  border-color: var(--accent);
}
.bg:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  height: 64px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--hairline);
}
.half {
  position: relative;
  display: flex;
  align-items: flex-end;
  padding: 5px;
}
.half:first-child {
  color: #f0a020;
}
.half:last-child {
  color: #e4e0ff;
}
.half svg {
  position: relative;
  filter: drop-shadow(0 1px 2px rgb(0 0 0 / 0.3));
}
.custom-half {
  justify-content: center;
  align-items: center;
  color: var(--text-3) !important;
  background: rgb(var(--surface-rgb) / 0.4);
}
.custom-half img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.custom-half.empty:first-child {
  border-right: 1px dashed var(--hairline);
}
.accents {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.acc {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 2px solid rgb(255 255 255 / 0.8);
  box-shadow: 0 1px 4px rgb(0 0 0 / 0.15);
  padding: 0;
}
.acc[aria-pressed='true'] {
  outline: 2px solid var(--text-1);
  outline-offset: 2px;
}
.custom {
  background: conic-gradient(red, yellow, lime, cyan, blue, magenta, red);
  position: relative;
  overflow: hidden;
  cursor: pointer;
}
.custom input {
  opacity: 0;
  position: absolute;
  inset: 0;
  cursor: pointer;
}
.note {
  font-size: 13px;
  margin: 0;
}
.walls {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.wall {
  display: grid;
  gap: 8px;
}
.wall-preview {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--hairline);
  display: grid;
  place-items: center;
  color: var(--text-3);
  background: rgb(var(--surface-rgb) / 0.45);
}
.wall-preview.empty {
  border-style: dashed;
}
.wall-preview img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.wall-tag {
  position: absolute;
  left: 8px;
  bottom: 8px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: var(--radius-pill);
  background: rgb(255 255 255 / 0.85);
  color: #1c2340;
  font-size: 12px;
  font-weight: 600;
}
.wall-actions {
  display: flex;
  gap: 6px;
}
</style>
