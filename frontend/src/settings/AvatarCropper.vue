<script setup lang="ts">
/**
 * Cadrage de la photo de profil : on fait glisser l'image dans le cercle et on règle le zoom
 * (souris, doigt, molette ou clavier). Le résultat est un carré de 512 px (WebP, sinon JPEG).
 */
import { PhMagnifyingGlassMinus, PhMagnifyingGlassPlus } from '@phosphor-icons/vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import GlassDialog from '@/design-system/components/GlassDialog.vue'
import { t } from '@/i18n'
import { coverScale, clampOffset, cropRect } from './crop'

const props = defineProps<{ file: Blob }>()
const emit = defineEmits<{ close: []; done: [blob: Blob] }>()

const VIEW = 280 // diamètre de la zone de cadrage (px)
const OUT = 512 // taille de l'image envoyée (px)
const url = URL.createObjectURL(props.file)
const img = ref<HTMLImageElement>()
const natural = ref({ w: 0, h: 0 })
const zoom = ref(1) // 1 = l'image couvre juste le cercle
const offset = ref({ x: 0, y: 0 }) // décalage du centre de l'image par rapport au centre du cercle (px écran)
const error = ref('')
const busy = ref(false)

const scale = computed(() => coverScale(natural.value, VIEW) * zoom.value)
const imgStyle = computed(() => ({
  width: `${natural.value.w * scale.value}px`,
  height: `${natural.value.h * scale.value}px`,
  transform: `translate(calc(-50% + ${offset.value.x}px), calc(-50% + ${offset.value.y}px))`,
}))

function onLoad() {
  const el = img.value!
  natural.value = { w: el.naturalWidth, h: el.naturalHeight }
  // Photo en hauteur : on part du haut (le visage y est presque toujours), pas du centre
  if (el.naturalHeight > el.naturalWidth) setOffset(0, (natural.value.h * scale.value - VIEW) * 0.35)
}
function onError() {
  error.value = t('Image illisible : utilisez une photo PNG, JPEG ou WebP.')
}
onBeforeUnmount(() => URL.revokeObjectURL(url))

function setOffset(x: number, y: number) {
  offset.value = clampOffset({ x, y }, natural.value, scale.value, VIEW)
}
function setZoom(z: number) {
  // Zoom autour du centre du cercle : le point visé reste au milieu
  const prev = scale.value
  zoom.value = Math.min(4, Math.max(1, z))
  const k = scale.value / prev
  setOffset(offset.value.x * k, offset.value.y * k)
}

// Glisser (souris et doigt)
let drag: { x: number; y: number; ox: number; oy: number } | null = null
function down(e: PointerEvent) {
  drag = { x: e.clientX, y: e.clientY, ox: offset.value.x, oy: offset.value.y }
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}
function move(e: PointerEvent) {
  if (drag) setOffset(drag.ox + e.clientX - drag.x, drag.oy + e.clientY - drag.y)
}
function up() {
  drag = null
}
function wheel(e: WheelEvent) {
  setZoom(zoom.value * (e.deltaY < 0 ? 1.08 : 1 / 1.08))
}
function key(e: KeyboardEvent) {
  const step = e.shiftKey ? 20 : 6
  const map: Record<string, () => void> = {
    ArrowLeft: () => setOffset(offset.value.x + step, offset.value.y),
    ArrowRight: () => setOffset(offset.value.x - step, offset.value.y),
    ArrowUp: () => setOffset(offset.value.x, offset.value.y + step),
    ArrowDown: () => setOffset(offset.value.x, offset.value.y - step),
    '+': () => setZoom(zoom.value * 1.1),
    '=': () => setZoom(zoom.value * 1.1),
    '-': () => setZoom(zoom.value / 1.1),
  }
  const fn = map[e.key]
  if (fn) {
    e.preventDefault()
    fn()
  }
}

async function confirm() {
  if (!img.value || !natural.value.w) return
  busy.value = true
  try {
    const r = cropRect(natural.value, scale.value, offset.value, VIEW)
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = OUT
    const ctx = canvas.getContext('2d')!
    ctx.imageSmoothingQuality = 'high'
    ctx.drawImage(img.value, r.x, r.y, r.size, r.size, 0, 0, OUT, OUT)
    const toBlob = (type: string) => new Promise<Blob | null>((res) => canvas.toBlob(res, type, 0.9))
    // WebP si le navigateur sait l'encoder, sinon JPEG
    let blob = await toBlob('image/webp')
    if (!blob || blob.type !== 'image/webp') blob = await toBlob('image/jpeg')
    if (!blob) throw new Error(t('Impossible de préparer la photo.'))
    emit('done', blob)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}

onMounted(() => document.querySelector<HTMLElement>('.crop-area')?.focus())
</script>

<template>
  <GlassDialog :title="$t('Cadrer la photo')" @close="emit('close')">
    <div class="cropper">
      <div
        class="crop-area"
        tabindex="0"
        role="application"
        :aria-label="$t('Zone de cadrage : flèches pour déplacer, + et − pour zoomer')"
        :style="{ width: `${VIEW}px`, height: `${VIEW}px` }"
        @pointerdown="down"
        @pointermove="move"
        @pointerup="up"
        @pointercancel="up"
        @wheel.prevent="wheel"
        @keydown="key"
      >
        <img ref="img" :src="url" alt="" draggable="false" :style="imgStyle" @load="onLoad" @error="onError" />
        <div class="mask" aria-hidden="true" />
      </div>
      <label class="zoom">
        <PhMagnifyingGlassMinus :size="18" aria-hidden="true" />
        <input
          type="range"
          min="1"
          max="4"
          step="0.01"
          :value="zoom"
          :aria-label="$t('Zoom')"
          @input="setZoom(Number(($event.target as HTMLInputElement).value))"
        />
        <PhMagnifyingGlassPlus :size="18" aria-hidden="true" />
      </label>
      <p class="faint hint">{{ $t('Faites glisser la photo pour la placer dans le cercle.') }}</p>
      <p v-if="error" class="error-text">{{ error }}</p>
    </div>
    <template #footer>
      <button class="btn" type="button" @click="emit('close')">{{ $t('Annuler') }}</button>
      <button class="btn primary" type="button" :disabled="busy || !natural.w" @click="confirm">{{ $t('Utiliser cette photo') }}</button>
    </template>
  </GlassDialog>
</template>

<style scoped>
.cropper {
  display: grid;
  justify-items: center;
  gap: 14px;
}
.crop-area {
  position: relative;
  max-width: 100%;
  overflow: hidden;
  border-radius: 16px;
  background: #111;
  cursor: grab;
  touch-action: none;
  user-select: none;
}
.crop-area:active {
  cursor: grabbing;
}
.crop-area img {
  position: absolute;
  left: 50%;
  top: 50%;
  max-width: none;
  pointer-events: none;
}
/* Voile autour du cercle : on voit ce qui sera coupé */
.mask {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  box-shadow: 0 0 0 999px rgb(0 0 0 / 0.55);
  outline: 2px solid rgb(255 255 255 / 0.85);
  outline-offset: -2px;
  pointer-events: none;
}
.zoom {
  display: flex;
  align-items: center;
  gap: 10px;
  width: min(280px, 100%);
  color: var(--text-2);
}
.zoom input {
  flex: 1;
}
.hint {
  margin: 0;
  font-size: 12.5px;
  text-align: center;
}
</style>
