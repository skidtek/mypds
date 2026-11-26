<script setup lang="ts">
/**
 * Rendu de la grille libre : positions absolues calculées (transitions fluides),
 * glisser-déposer à la souris / au doigt, redimensionnement, et déplacement au clavier.
 * La barre de recherche sert de rail : les autres widgets restent entre ses bords (grid.ts).
 */
import { PhArrowsOutSimple } from '@phosphor-icons/vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Widget } from '@/api/types'
import { useLanding } from '@/stores/landing'
import { type Breakpoint, clampSpan, COLS, compact, dragLayout, type Item, railId, railSpan, resizeLayout, resolveGrid, resolveMobile, sameLayout, SIZES, type Span } from './grid'
import WidgetFrame from './WidgetFrame.vue'
import { t } from '@/i18n'
import { WIDGET_NAMES } from '@/widgets/names'

const props = defineProps<{ bp: Breakpoint }>()
const emit = defineEmits<{ configure: [id: string] }>()
const store = useLanding()

const ROW = { desktop: 52, tablet: 54, mobile: 54 }
const GAP = { desktop: 18, tablet: 16, mobile: 14 }

const container = ref<HTMLElement>()
const width = ref(0)
const preview = ref<Item[] | null>(null)
const active = ref<{ id: string; mode: 'move' | 'resize'; px: number; py: number; left: number; top: number; w: number; h: number } | null>(null)
const announce = ref('')

const cols = computed(() => COLS[props.bp])
const rowH = computed(() => ROW[props.bp])
const gap = computed(() => GAP[props.bp])
const colW = computed(() => (width.value - gap.value * (cols.value - 1)) / cols.value)

// ---------- Rail (barre de recherche) ----------
const isGrid = computed(() => props.bp !== 'mobile')
const rail = computed(() => (isGrid.value && store.doc ? railId(store.doc.widgets) : undefined))
const savedSpan = computed<Span>(() =>
  isGrid.value && store.doc ? railSpan(store.doc.widgets, props.bp as 'desktop' | 'tablet') : { x: 0, w: cols.value },
)
const previewSpan = ref<Span | null>(null)
const span = computed(() => previewSpan.value ?? savedSpan.value)
const spanLeft = computed(() => span.value.x * (colW.value + gap.value))
const spanW = computed(() => span.value.w * colW.value + (span.value.w - 1) * gap.value)
/** Colonnes intérieures au rail, où se placent les autres widgets. */
const innerW = computed(() => (spanW.value - gap.value * (cols.value - 1)) / cols.value)
const isRail = (id: string) => id === rail.value

const resolved = computed<Item[]>(() => {
  const doc = store.doc
  if (!doc) return []
  return props.bp === 'mobile' ? resolveMobile(doc) : resolveGrid(doc.widgets, props.bp)
})
const items = computed(() => preview.value ?? resolved.value)
const byId = computed(() => new Map(store.widgets.map((w) => [w.id, w])))
const height = computed(() => {
  const bottom = Math.max(0, ...items.value.map((i) => i.y + i.h))
  return bottom * (rowH.value + gap.value) - gap.value
})

function rect(it: Item) {
  const top = it.y * (rowH.value + gap.value)
  const height = it.h * rowH.value + (it.h - 1) * gap.value
  if (isRail(it.id)) return { left: spanLeft.value, top, width: spanW.value, height }
  return {
    left: spanLeft.value + it.x * (innerW.value + gap.value),
    top,
    width: it.w * innerW.value + (it.w - 1) * gap.value,
    height,
  }
}

function styleFor(it: Item) {
  const a = active.value
  if (a && a.id === it.id) {
    return { transform: `translate(${a.left}px, ${a.top}px)`, width: `${a.w}px`, height: `${a.h}px` }
  }
  const r = rect(it)
  return { transform: `translate(${r.left}px, ${r.top}px)`, width: `${r.width}px`, height: `${r.height}px` }
}

function spec(id: string) {
  const w = byId.value.get(id)
  if (!w) return undefined
  const s = SIZES[w.type]
  return props.bp === 'mobile' ? { ...s, minW: 1, w: 1, maxH: 10 } : s
}

function commit(next: Item[], nextSpan: Span = span.value) {
  const final = compact(next)
  const spanChanged = nextSpan.x !== savedSpan.value.x || nextSpan.w !== savedSpan.value.w
  if (!sameLayout(final, resolved.value) || spanChanged) {
    if (props.bp === 'mobile') store.commitMobile(final)
    // Le rail est stocké avec sa largeur réelle (le moteur le traite en pleine largeur)
    else store.commitGrid(props.bp, final.map((i) => (isRail(i.id) ? { ...i, x: nextSpan.x, w: nextSpan.w } : i)))
  }
  preview.value = null
  previewSpan.value = null
}

// ---------- Souris / tactile ----------
let base: Item[] = []
let dragSpan: Span = { x: 0, w: 12 }

function start(e: PointerEvent, id: string, mode: 'move' | 'resize') {
  if (!store.editing || e.button !== 0) return
  const target = e.target as HTMLElement
  if (mode === 'move' && target.closest('button, a, input, select, textarea')) return
  e.preventDefault()
  const it = items.value.find((i) => i.id === id)
  if (!it) return
  base = items.value.map((i) => ({ ...i }))
  dragSpan = { ...span.value }
  const r = rect(it)
  active.value = { id, mode, px: e.clientX, py: e.clientY, left: r.left, top: r.top, w: r.width, h: r.height }
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

function move(e: PointerEvent) {
  const a = active.value
  if (!a) return
  const dx = e.clientX - a.px
  const dy = e.clientY - a.py
  const orig = base.find((i) => i.id === a.id)!
  const r0 = rect(orig)
  const rowStep = rowH.value + gap.value
  if (a.mode === 'move') {
    a.left = r0.left + dx
    a.top = r0.top + dy
    const y = Math.max(0, Math.round(a.top / rowStep))
    if (isRail(a.id)) {
      // Le rail glisse sur les colonnes de la page ; il garde ses rangées pour lui seul
      previewSpan.value = clampSpan({ x: Math.round(a.left / (colW.value + gap.value)), w: dragSpan.w }, props.bp as 'desktop' | 'tablet')
      preview.value = dragLayout(base, a.id, 0, y, cols.value, spec(a.id))
    } else {
      const x = Math.round((a.left - spanLeft.value) / (innerW.value + gap.value))
      preview.value = dragLayout(base, a.id, props.bp === 'mobile' ? 0 : x, y, cols.value, spec(a.id))
    }
    // Aimant : la tuile ne sort jamais du rail
    if (!isRail(a.id) && isGrid.value) a.left = Math.max(spanLeft.value, Math.min(a.left, spanLeft.value + spanW.value - a.w))
  } else {
    a.h = Math.max(rowH.value, r0.height + dy)
    const h = Math.round((a.h + gap.value) / rowStep)
    if (isRail(a.id)) {
      a.w = Math.max(colW.value, Math.min(r0.width + dx, width.value - a.left))
      previewSpan.value = clampSpan({ x: dragSpan.x, w: Math.round((a.w + gap.value) / (colW.value + gap.value)) }, props.bp as 'desktop' | 'tablet')
      preview.value = resizeLayout(base, a.id, cols.value, h, cols.value, spec(a.id))
    } else {
      a.w = Math.max(innerW.value, Math.min(r0.width + dx, spanLeft.value + spanW.value - a.left))
      const w = props.bp === 'mobile' ? 1 : Math.round((a.w + gap.value) / (innerW.value + gap.value))
      preview.value = resizeLayout(base, a.id, w, h, cols.value, spec(a.id))
    }
  }
}

function end(e?: PointerEvent) {
  if (!active.value) return
  if (e && e.type === 'pointerup') move(e) // position finale = position au relâchement
  const next = preview.value
  const nextSpan = previewSpan.value ?? span.value
  active.value = null
  if (next) commit(next, nextSpan)
}

// ---------- Clavier ----------
function onKey(e: KeyboardEvent, id: string) {
  if (!store.editing) return
  const deltas: Record<string, [number, number]> = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }
  const d = deltas[e.key]
  if (!d) return
  e.preventDefault()
  const it = items.value.find((i) => i.id === id)
  if (!it) return
  const cur = items.value.map((i) => ({ ...i }))
  if (isRail(id) && d[0] !== 0) {
    // Rail : gauche / droite le décale, Maj + gauche / droite change sa largeur
    const sp = span.value
    const next = e.shiftKey ? { x: sp.x, w: sp.w + d[0] } : { x: sp.x + d[0], w: sp.w }
    commit(cur, clampSpan(next, props.bp as 'desktop' | 'tablet'))
    requestAnimationFrame(() => (announce.value = describe(byId.value.get(id)!, it)))
    return
  }
  const overlapsX = (o: Item) => o.id !== id && o.x < it.x + it.w && it.x < o.x + o.w
  let y = it.y + d[1]
  if (d[1] > 0) {
    // Passer sous le voisin du dessous : il prend la place libérée
    const below = cur.filter((o) => overlapsX(o) && o.y >= it.y + it.h).sort((a, b) => a.y - b.y)[0]
    y = below ? it.y + below.h : it.y + 1
  } else if (d[1] < 0) {
    const above = cur.filter((o) => overlapsX(o) && o.y + o.h <= it.y).sort((a, b) => b.y - a.y)[0]
    y = above ? above.y : Math.max(0, it.y - 1)
  }
  let x = it.x + d[0]
  if (d[0] !== 0) {
    // Voisin direct sur la même rangée : échange de places
    const overlapsY = (o: Item) => o.id !== id && o.y < it.y + it.h && it.y < o.y + o.h
    const side = cur
      .filter((o) => overlapsY(o) && (d[0] > 0 ? o.x >= it.x + it.w : o.x + o.w <= it.x))
      .sort((a, b) => (d[0] > 0 ? a.x - b.x : b.x - a.x))[0]
    const adjacent = side && (d[0] > 0 ? side.x === it.x + it.w : side.x + side.w === it.x)
    if (side && adjacent) x = d[0] > 0 ? side.x + side.w - it.w : side.x
  }
  const next = e.shiftKey
    ? resizeLayout(cur, id, it.w + d[0], it.h + d[1], cols.value, spec(id))
    : dragLayout(cur, id, x, y, cols.value, spec(id))
  commit(next)
  requestAnimationFrame(() => {
    const now = resolved.value.find((i) => i.id === id)
    if (now) announce.value = describe(byId.value.get(id)!, now)
  })
}

function label(w: Widget): string {
  return w.title || t(WIDGET_NAMES[w.type])
}

function describe(w: Widget, it: Item): string {
  if (props.bp === 'mobile')
    return t('{name} : position {pos}, hauteur {h}', { name: label(w), pos: items.value.filter((i) => i.y < it.y).length + 1, h: it.h })
  const pos = isRail(it.id) ? { x: span.value.x + 1, w: span.value.w } : { x: it.x + 1, w: it.w }
  return t('{name} : colonne {x}, ligne {y}, {w} colonnes sur {h} lignes', { name: label(w), x: pos.x, y: it.y + 1, w: pos.w, h: it.h })
}

let ro: ResizeObserver | undefined
onMounted(() => {
  ro = new ResizeObserver(([entry]) => (width.value = entry!.contentRect.width))
  if (container.value) ro.observe(container.value)
})
onBeforeUnmount(() => ro?.disconnect())
watch(
  () => store.editing,
  (v) => {
    if (!v) {
      active.value = null
      preview.value = null
      previewSpan.value = null
    }
  },
)
</script>

<template>
  <div ref="container" class="grid" :class="{ editing: store.editing, dragging: !!active }" :style="{ height: `${Math.max(height, 0)}px` }">
    <template v-if="width > 0">
      <div
        v-for="it in items"
        :key="it.id"
        class="cell"
        :class="{ active: active?.id === it.id, search: byId.get(it.id)?.type === 'search' }"
        :style="styleFor(it)"
        :tabindex="store.editing ? 0 : -1"
        :role="store.editing ? 'group' : undefined"
        :aria-roledescription="store.editing ? $t('widget déplaçable') : undefined"
        :aria-label="store.editing && byId.get(it.id) ? `${describe(byId.get(it.id)!, it)}. ${$t('Flèches pour déplacer, Maj + flèches pour redimensionner.')}` : undefined"
        @pointerdown="start($event, it.id, 'move')"
        @pointermove="move"
        @pointerup="end"
        @pointercancel="end"
        @keydown="onKey($event, it.id)"
      >
        <WidgetFrame v-if="byId.get(it.id)" :widget="byId.get(it.id)!" @configure="emit('configure', it.id)" />
        <span
          v-if="store.editing"
          class="resize"
          aria-hidden="true"
          @pointerdown.stop="start($event, it.id, 'resize')"
          @pointermove="move"
          @pointerup="end"
          @pointercancel="end"
        >
          <PhArrowsOutSimple :size="14" weight="bold" />
        </span>
      </div>
    </template>
    <p class="sr-only" aria-live="polite">{{ announce }}</p>
  </div>
</template>

<style scoped>
.grid {
  position: relative;
  width: 100%;
  transition: height var(--dur) var(--ease);
}
.cell {
  position: absolute;
  top: 0;
  left: 0;
  transition:
    transform var(--dur) var(--ease),
    width var(--dur) var(--ease),
    height var(--dur) var(--ease);
  will-change: transform;
}
.cell.active {
  transition: none;
  z-index: 20;
  cursor: grabbing;
}
.editing .cell {
  touch-action: none;
  cursor: grab;
  user-select: none;
}
.editing .cell:focus-visible {
  outline: none;
  box-shadow: none;
}
.editing .cell:focus-visible :deep(.frame) {
  box-shadow: var(--focus-ring), var(--shadow-card);
}
.resize {
  position: absolute;
  right: 6px;
  bottom: 6px;
  width: 26px;
  height: 26px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  background: var(--surface-strong);
  border: 1px solid var(--surface-border);
  color: var(--text-2);
  cursor: nwse-resize;
  touch-action: none;
  z-index: 3;
  transform: rotate(90deg);
}
</style>
