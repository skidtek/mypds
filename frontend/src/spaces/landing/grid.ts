/**
 * Moteur de disposition libre de la Landing Page (ADR-0008).
 * Fonctions pures : placement automatique, compactage vertical, déplacement et
 * redimensionnement avec poussée des voisins. Aucune dépendance au Cockpit.
 */
import type { LandingDocument, Placement, Widget, WidgetType } from '@/api/types'

export type Breakpoint = 'desktop' | 'tablet' | 'mobile'
export const COLS: Record<Breakpoint, number> = { desktop: 12, tablet: 8, mobile: 1 }

export interface Item {
  id: string
  x: number
  y: number
  w: number
  h: number
}

export interface SizeSpec {
  w: number
  h: number
  minW: number
  minH: number
  maxH: number
  mobileH: number
}

export const SIZES: Record<WidgetType, SizeSpec> = {
  search: { w: 12, h: 1, minW: 4, minH: 1, maxH: 2, mobileH: 1 },
  weather: { w: 6, h: 3, minW: 3, minH: 2, maxH: 6, mobileH: 3 },
  calendar: { w: 6, h: 3, minW: 3, minH: 2, maxH: 8, mobileH: 4 },
  news: { w: 12, h: 4, minW: 4, minH: 3, maxH: 8, mobileH: 5 },
  todo: { w: 4, h: 4, minW: 3, minH: 3, maxH: 10, mobileH: 5 },
  note: { w: 4, h: 4, minW: 3, minH: 3, maxH: 10, mobileH: 5 },
}

/**
 * Rail : la première barre de recherche visible fixe les bords gauche et droit de la grille.
 * Elle occupe seule ses rangées (pleine largeur pour les collisions) ; les autres widgets se
 * placent sur les colonnes *à l'intérieur* de sa largeur, sans jamais la dépasser.
 */
export interface Span {
  x: number
  w: number
}
export const RAIL_MIN: Record<'desktop' | 'tablet', number> = { desktop: 6, tablet: 4 }

export function railId(widgets: Widget[]): string | undefined {
  return widgets.find((w) => w.type === 'search' && !w.hidden)?.id
}

export function clampSpan(sp: Span, bp: 'desktop' | 'tablet'): Span {
  const cols = COLS[bp]
  const w = Math.max(RAIL_MIN[bp], Math.min(sp.w, cols))
  return { x: Math.max(0, Math.min(sp.x, cols - w)), w }
}

/** Largeur et position du rail (colonnes de la grille) ; toute la largeur sans barre de recherche. */
export function railSpan(widgets: Widget[], bp: 'desktop' | 'tablet'): Span {
  const id = railId(widgets)
  const w = id ? widgets.find((x) => x.id === id) : undefined
  const p = w && (bp === 'desktop' ? w.placement.desktop : (w.placement.tablet ?? (w.placement.desktop && scaleToTablet(w.placement.desktop))))
  return p ? clampSpan({ x: p.x, w: p.w }, bp) : { x: 0, w: COLS[bp] }
}

export function breakpointFor(width: number): Breakpoint {
  if (width >= 1024) return 'desktop'
  if (width >= 700) return 'tablet'
  return 'mobile'
}

export function collides(a: Item, b: Item): boolean {
  return a.id !== b.id && a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h
}

const byPosition = (a: Item, b: Item) => a.y - b.y || a.x - b.x

export function clampItem(it: Item, cols: number, spec?: SizeSpec): Item {
  const minW = Math.min(spec?.minW ?? 1, cols)
  const w = Math.max(minW, Math.min(it.w, cols))
  const h = Math.max(spec?.minH ?? 1, Math.min(it.h, spec?.maxH ?? 12))
  return { id: it.id, w, h, x: Math.max(0, Math.min(it.x, cols - w)), y: Math.max(0, it.y) }
}

/** Remonte chaque élément jusqu'au premier obstacle ; résout les chevauchements en descendant. */
export function compact(items: Item[], pinnedId?: string): Item[] {
  const pinned = pinnedId ? items.find((i) => i.id === pinnedId) : undefined
  const placed: Item[] = pinned ? [{ ...pinned }] : []
  for (const it of [...items].sort(byPosition)) {
    if (it.id === pinnedId) continue
    const c = { ...it, y: Math.max(0, it.y) }
    pushDown(c, placed)
    while (c.y > 0 && !placed.some((p) => collides({ ...c, y: c.y - 1 }, p))) c.y--
    placed.push(c)
  }
  return placed
}

function pushDown(c: Item, placed: Item[]) {
  let hits = placed.filter((p) => collides(c, p))
  while (hits.length) {
    c.y = Math.max(...hits.map((p) => p.y + p.h))
    hits = placed.filter((p) => collides(c, p))
  }
}

export function firstFit(placed: Item[], id: string, w: number, h: number, cols: number): Item {
  for (let y = 0; y < 1000; y++) {
    for (let x = 0; x + w <= cols; x++) {
      const c = { id, x, y, w, h }
      if (!placed.some((p) => collides(c, p))) return c
    }
  }
  return { id, x: 0, y: 1000, w, h }
}

function scaleToTablet(p: Placement): Placement {
  const ratio = COLS.tablet / COLS.desktop
  const w = Math.max(1, Math.round(p.w * ratio))
  return { x: Math.min(Math.round(p.x * ratio), COLS.tablet - w), y: p.y, w, h: p.h }
}

/** Calcule la disposition affichée pour un point de rupture desktop ou tablette. */
export function resolveGrid(widgets: Widget[], bp: 'desktop' | 'tablet'): Item[] {
  const cols = COLS[bp]
  const rail = railId(widgets)
  const fixed: Item[] = []
  const auto: Widget[] = []
  for (const w of widgets) {
    if (w.hidden) continue
    const p = bp === 'desktop' ? w.placement.desktop : (w.placement.tablet ?? (w.placement.desktop && scaleToTablet(w.placement.desktop)))
    // Le rail réserve ses rangées sur toute la largeur ; sa largeur réelle est donnée par railSpan()
    if (p) fixed.push(clampItem({ id: w.id, ...p, ...(w.id === rail ? { x: 0, w: cols } : {}) }, cols, SIZES[w.type]))
    else auto.push(w)
  }
  let items = compact(fixed)
  for (const w of auto) {
    const s = SIZES[w.type]
    items.push(firstFit(items, w.id, w.id === rail ? cols : Math.min(s.w, cols), s.h, cols))
  }
  items = compact(items)
  return items
}

/** Ordre mobile : personnalisé, ou dérivé de la lecture desktop (haut → bas, gauche → droite). */
export function mobileOrder(doc: LandingDocument): string[] {
  const desktop = resolveGrid(doc.widgets, 'desktop').sort(byPosition).map((i) => i.id)
  if (doc.mobile.mode !== 'custom') return desktop
  const visible = new Set(desktop)
  const custom = doc.mobile.order.filter((id) => visible.has(id))
  return [...custom, ...desktop.filter((id) => !custom.includes(id))]
}

export function resolveMobile(doc: LandingDocument): Item[] {
  const byId = new Map(doc.widgets.map((w) => [w.id, w]))
  let y = 0
  return mobileOrder(doc).map((id) => {
    const w = byId.get(id)!
    const h = w.placement.mobile_h ?? SIZES[w.type].mobileH
    const it = { id, x: 0, y, w: 1, h }
    y += h
    return it
  })
}

/**
 * Disposition pendant un glisser-déposer. Calculée depuis l'état initial `base` (pas de dérive) :
 * l'élément déplacé est fixe, les voisins s'écartent puis se compactent autour de lui.
 */
export function dragLayout(base: Item[], id: string, x: number, y: number, cols: number, spec?: SizeSpec): Item[] {
  const orig = base.find((i) => i.id === id)
  if (!orig) return base
  const moving = clampItem({ ...orig, x, y }, cols, spec)
  const movingDown = moving.y > orig.y
  const placed: Item[] = [moving]
  for (const o of base.filter((i) => i.id !== id).sort(byPosition)) {
    const c = { ...o }
    if (collides(c, moving)) {
      // 1) descente : le voisin remonte au-dessus ; 2) sinon il prend la place libérée (échange)
      const candidates = movingDown ? [{ ...c, y: moving.y - c.h }] : []
      candidates.push({ ...c, x: orig.x, y: orig.y })
      const free = candidates.find((k) => k.y >= 0 && k.x + k.w <= cols && !placed.some((p) => collides(k, p)))
      if (free) Object.assign(c, { x: free.x, y: free.y })
    }
    pushDown(c, placed)
    placed.push(c)
  }
  return compact(placed, id)
}

export function resizeLayout(base: Item[], id: string, w: number, h: number, cols: number, spec?: SizeSpec): Item[] {
  const orig = base.find((i) => i.id === id)
  if (!orig) return base
  const sized = clampItem({ ...orig, w, h }, cols, spec)
  const placed: Item[] = [sized]
  for (const o of base.filter((i) => i.id !== id).sort(byPosition)) {
    const c = { ...o }
    pushDown(c, placed)
    placed.push(c)
  }
  return compact(placed, id)
}

export function sameLayout(a: Item[], b: Item[]): boolean {
  if (a.length !== b.length) return false
  const m = new Map(b.map((i) => [i.id, i]))
  return a.every((i) => {
    const j = m.get(i.id)
    return j && j.x === i.x && j.y === i.y && j.w === i.w && j.h === i.h
  })
}
