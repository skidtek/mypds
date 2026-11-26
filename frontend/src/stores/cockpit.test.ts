import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useCockpit } from './cockpit'

vi.mock('@/api/client', () => ({ api: vi.fn(async () => ({ revision: 2 })), ApiError: class extends Error {} }))

const tile = (id: string) => ({ id, type: 'link' as const, width: { desktop: 3 }, config: { label: id, url: 'https://x' } })

describe('cockpit store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const s = useCockpit()
    s.doc = {
      schema: 'mypds.cockpit-layout',
      version: 1,
      groups: [
        { id: 'g_a', title: 'A', rows: [{ id: 'r_1', tiles: [tile('t_1'), tile('t_2')] }, { id: 'r_2', tiles: [] }] },
        { id: 'g_b', title: 'B', rows: [{ id: 'r_3', tiles: [] }] },
      ],
    }
  })

  it('déplace une tuile vers un autre groupe uniquement par action explicite', () => {
    const s = useCockpit()
    s.moveTileToGroup('t_1', 'g_b')
    expect(s.group('g_a')!.rows[0]!.tiles.map((t) => t.id)).toEqual(['t_2'])
    expect(s.group('g_b')!.rows[0]!.tiles.map((t) => t.id)).toEqual(['t_1'])
  })

  it('réordonne les lignes et les groupes sans sortir des bornes', () => {
    const s = useCockpit()
    s.moveRow('g_a', 'r_2', -1)
    expect(s.group('g_a')!.rows.map((r) => r.id)).toEqual(['r_2', 'r_1'])
    s.moveRow('g_a', 'r_2', -1)
    expect(s.group('g_a')!.rows.map((r) => r.id)).toEqual(['r_2', 'r_1'])
    s.moveGroup('g_b', -1)
    expect(s.doc!.groups.map((g) => g.id)).toEqual(['g_b', 'g_a'])
  })

  it('garde toujours au moins un onglet', () => {
    const s = useCockpit()
    s.removeGroup('g_a')
    s.removeGroup('g_b')
    expect(s.doc!.groups).toHaveLength(1)
  })

  it('ajoute une tuile avec un identifiant valide', () => {
    const s = useCockpit()
    s.addTile('g_b', 'r_3', { type: 'link', width: { desktop: 4 }, config: { label: 'GRR', url: 'https://grr.lan' } })
    expect(s.group('g_b')!.rows[0]!.tiles[0]!.id).toMatch(/^t_[a-f0-9]{12}$/)
  })
})
