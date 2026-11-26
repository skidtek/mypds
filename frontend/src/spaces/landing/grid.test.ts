import { describe, expect, it } from 'vitest'
import type { LandingDocument, Widget } from '@/api/types'
import { clampSpan, collides, compact, dragLayout, type Item, mobileOrder, railSpan, resizeLayout, resolveGrid, resolveMobile } from './grid'

const w = (id: string, type: Widget['type'], desktop: Item | null = null, extra: Partial<Widget> = {}): Widget => ({
  id,
  type,
  title: null,
  hidden: false,
  config: {},
  placement: { desktop: desktop && { x: desktop.x, y: desktop.y, w: desktop.w, h: desktop.h }, tablet: null, mobile_h: null },
  ...extra,
})

const noOverlap = (items: Item[]) => items.every((a) => items.every((b) => !collides(a, b)))
const at = (items: Item[], id: string) => items.find((i) => i.id === id)!

describe('compact', () => {
  it('remonte les éléments et supprime les chevauchements', () => {
    const out = compact([
      { id: 'a', x: 0, y: 5, w: 6, h: 2 },
      { id: 'b', x: 0, y: 5, w: 6, h: 2 },
    ])
    expect(at(out, 'a').y).toBe(0)
    expect(at(out, 'b').y).toBe(2)
    expect(noOverlap(out)).toBe(true)
  })
})

describe('resolveGrid', () => {
  it('place automatiquement les widgets sans position', () => {
    const items = resolveGrid([w('s', 'search', { id: 's', x: 0, y: 0, w: 12, h: 1 }), w('a', 'weather'), w('b', 'calendar')], 'desktop')
    expect(at(items, 'a')).toMatchObject({ x: 0, y: 1, w: 6 })
    expect(at(items, 'b')).toMatchObject({ x: 6, y: 1, w: 6 })
    expect(noOverlap(items)).toBe(true)
  })

  it('ignore les widgets masqués et dérive la tablette du desktop', () => {
    const items = resolveGrid([w('a', 'weather', { id: 'a', x: 6, y: 0, w: 6, h: 3 }), w('h', 'news', null, { hidden: true })], 'tablet')
    expect(items).toHaveLength(1)
    expect(at(items, 'a')).toMatchObject({ x: 4, w: 4 })
  })

  it('borne un widget qui dépasserait la grille', () => {
    const items = resolveGrid([w('a', 'news', { id: 'a', x: 10, y: 0, w: 12, h: 4 })], 'desktop')
    expect(at(items, 'a')).toMatchObject({ x: 0, w: 12 })
  })
})

describe('dragLayout', () => {
  const base: Item[] = [
    { id: 'a', x: 0, y: 0, w: 12, h: 2 },
    { id: 'b', x: 0, y: 2, w: 12, h: 3 },
  ]
  it('permet de descendre un widget sous son voisin (échange)', () => {
    const preview = dragLayout(base, 'a', 0, 3, 12)
    const final = compact(preview)
    expect(at(final, 'b').y).toBe(0)
    expect(at(final, 'a').y).toBe(3)
  })
  it('pousse les voisins quand on remonte', () => {
    const final = compact(dragLayout(base, 'b', 0, 0, 12))
    expect(at(final, 'b').y).toBe(0)
    expect(at(final, 'a').y).toBe(3)
    expect(noOverlap(final)).toBe(true)
  })
  it('échange deux widgets côte à côte', () => {
    const row: Item[] = [
      { id: 'w', x: 0, y: 1, w: 6, h: 3 },
      { id: 'c', x: 6, y: 1, w: 6, h: 3 },
    ]
    const final = compact(dragLayout(row, 'w', 6, 1, 12))
    expect(at(final, 'w')).toMatchObject({ x: 6, y: 0 })
    expect(at(final, 'c')).toMatchObject({ x: 0, y: 0 })
  })
  it('place côte à côte', () => {
    const two: Item[] = [
      { id: 'a', x: 0, y: 0, w: 6, h: 3 },
      { id: 'b', x: 0, y: 3, w: 6, h: 3 },
    ]
    const final = compact(dragLayout(two, 'b', 6, 0, 12))
    expect(at(final, 'b')).toMatchObject({ x: 6, y: 0 })
  })
})

describe('resizeLayout', () => {
  it('écarte les voisins quand un widget grandit', () => {
    const base: Item[] = [
      { id: 'a', x: 0, y: 0, w: 6, h: 2 },
      { id: 'b', x: 0, y: 2, w: 6, h: 2 },
    ]
    const out = compact(resizeLayout(base, 'a', 6, 4, 12))
    expect(at(out, 'b').y).toBe(4)
    expect(noOverlap(out)).toBe(true)
  })
})

describe('mobile', () => {
  const doc = (mode: 'auto' | 'custom', order: string[] = []): LandingDocument => ({
    schema: 'mypds.landing-layout',
    version: 1,
    widgets: [w('n', 'news', { id: 'n', x: 0, y: 4, w: 12, h: 4 }), w('a', 'weather', { id: 'a', x: 6, y: 0, w: 6, h: 3 }), w('c', 'calendar', { id: 'c', x: 0, y: 0, w: 6, h: 3 })],
    mobile: { mode, order },
  })
  it("suit la lecture desktop en mode automatique", () => {
    expect(mobileOrder(doc('auto'))).toEqual(['c', 'a', 'n'])
  })
  it('respecte un ordre personnalisé et ajoute les nouveaux widgets à la fin', () => {
    expect(mobileOrder(doc('custom', ['n', 'a']))).toEqual(['n', 'a', 'c'])
  })
  it('empile en une colonne sans chevauchement', () => {
    const items = resolveMobile(doc('auto'))
    expect(items.every((i) => i.x === 0 && i.w === 1)).toBe(true)
    expect(noOverlap(items)).toBe(true)
  })
})

describe('rail (barre de recherche)', () => {
  it('fixe les bords de la grille et réserve ses rangées', () => {
    const ws = [
      w('s', 'search', { id: 's', x: 2, y: 0, w: 8, h: 1 }),
      w('m', 'weather', { id: 'm', x: 10, y: 0, w: 2, h: 3 }), // à côté de la recherche : interdit
    ]
    expect(railSpan(ws, 'desktop')).toEqual({ x: 2, w: 8 })
    const out = resolveGrid(ws, 'desktop')
    expect(at(out, 's')).toMatchObject({ x: 0, w: 12 })
    expect(at(out, 'm').y).toBeGreaterThanOrEqual(1)
    expect(noOverlap(out)).toBe(true)
  })

  it('garde une largeur minimale lisible et reste dans la page', () => {
    expect(clampSpan({ x: 10, w: 2 }, 'desktop')).toEqual({ x: 6, w: 6 })
    expect(clampSpan({ x: -3, w: 20 }, 'tablet')).toEqual({ x: 0, w: 8 })
  })

  it('prend toute la largeur sans barre de recherche', () => {
    expect(railSpan([w('m', 'weather', { id: 'm', x: 0, y: 0, w: 6, h: 3 })], 'desktop')).toEqual({ x: 0, w: 12 })
  })
})
