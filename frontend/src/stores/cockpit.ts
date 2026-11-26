import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, ApiError } from '@/api/client'
import type { AlertItem, CockpitDocument, CockpitGroup, CockpitRow, CockpitTile, ConnectorSnapshot, PveGuest, PveTask } from '@/api/types'
import { randomHex } from '@/design-system/id'
import type { SaveStatus } from './landing'

const rid = (p: 'g' | 'r' | 't') => `${p}_${randomHex()}`

export const useCockpit = defineStore('cockpit', () => {
  const doc = ref<CockpitDocument | null>(null)
  const revision = ref(0)
  const status = ref<SaveStatus>('idle')
  const error = ref('')
  const editing = ref(false)
  const snapshots = ref<ConnectorSnapshot[]>([])
  const snapshotsError = ref('')
  const alerts = ref<AlertItem[]>([])
  const resolved = ref<AlertItem[]>([])
  const alertsLoaded = ref(false)
  let timer: number | undefined
  let inflight: Promise<void> | null = null

  async function load() {
    const res = await api<{ revision: number; document: CockpitDocument }>('/api/v1/cockpit/layout')
    doc.value = res.document
    revision.value = res.revision
  }

  async function loadSnapshots() {
    try {
      const [snaps, al] = await Promise.all([
        api<ConnectorSnapshot[]>('/api/v1/connectors/snapshots'),
        api<{ active: AlertItem[]; resolved: AlertItem[] }>('/api/v1/alerts'),
      ])
      snapshots.value = snaps
      alerts.value = al.active
      resolved.value = al.resolved
      alertsLoaded.value = true
      snapshotsError.value = ''
    } catch (e) {
      snapshotsError.value = e instanceof Error ? e.message : String(e)
    }
  }

  const snapshot = (id?: string) => snapshots.value.find((s) => s.id === id)
  const guest = (connectorId?: string, guestId?: string): PveGuest | undefined =>
    snapshot(connectorId)?.data?.guest_list.find((g) => g.id === guestId)
  const anyDemo = computed(() => snapshots.value.some((s) => s.demo))

  /** Dernières tâches de toutes les connexions, les plus récentes d'abord. */
  const tasks = computed(() =>
    snapshots.value
      .flatMap((s) => (s.data?.tasks ?? []).map((t) => ({ ...t, connector: s.name, demo: s.demo }) as PveTask & { connector: string; demo: boolean }))
      .sort((a, b) => b.start - a.start),
  )

  async function setOnDemand(connectorId: string, guestId: string, onDemand: boolean) {
    await api(`/api/v1/connectors/${connectorId}/on-demand`, { method: 'POST', json: { guest: guestId, on_demand: onDemand } })
    await loadSnapshots()
  }

  /** Vue d'ensemble : invités suivis, en marche, arrêtés ; nœuds hors ligne ; connecteurs en erreur. */
  const overview = computed(() => {
    let total = 0
    let stopped = 0
    let nodesDown = 0
    let failing = 0
    for (const s of snapshots.value) {
      if (!s.data) {
        failing += 1
        continue
      }
      if (s.status !== 'ok') failing += 1
      const d = s.data as unknown as Record<string, unknown>
      if (s.type === 'proxmox') {
        total += s.data.guest_list.length
        stopped += s.data.guest_list.filter((g) => g.status !== 'running').length
        nodesDown += s.data.nodes.filter((n) => !n.online).length
      } else if (s.type === 'docker') {
        const cs = (d.containers as { state: string }[] | undefined) ?? []
        total += cs.length
        stopped += cs.filter((c) => c.state !== 'running').length
      } else if (s.type === 'unifi') {
        const ds = (d.devices as { online: boolean }[] | undefined) ?? []
        nodesDown += ds.filter((x) => !x.online).length
      }
    }
    return { total, stopped, nodesDown, failing, ok: total > 0 && !stopped && !nodesDown && !failing }
  })

  async function flush() {
    if (!doc.value) return
    window.clearTimeout(timer)
    if (inflight) await inflight
    status.value = 'saving'
    inflight = (async () => {
      try {
        const res = await api<{ revision: number }>('/api/v1/cockpit/layout', {
          method: 'PUT',
          json: { revision: revision.value, document: doc.value },
        })
        revision.value = res.revision
        status.value = 'saved'
      } catch (e) {
        status.value = e instanceof ApiError && e.status === 409 ? 'conflict' : 'error'
        error.value = e instanceof Error ? e.message : String(e)
      } finally {
        inflight = null
      }
    })()
    await inflight
  }

  function save() {
    status.value = 'saving'
    window.clearTimeout(timer)
    timer = window.setTimeout(() => void flush(), 700)
  }

  const group = (id: string) => doc.value?.groups.find((g) => g.id === id)

  function findTile(tileId: string): { group: CockpitGroup; row: CockpitRow; tile: CockpitTile } | undefined {
    for (const g of doc.value?.groups ?? [])
      for (const r of g.rows) {
        const tile = r.tiles.find((t) => t.id === tileId)
        if (tile) return { group: g, row: r, tile }
      }
    return undefined
  }

  // ----- Groupes (onglets) -----
  function addGroup(title: string): string {
    const g: CockpitGroup = { id: rid('g'), title, rows: [{ id: rid('r'), tiles: [] }] }
    doc.value?.groups.push(g)
    save()
    return g.id
  }
  function renameGroup(id: string, title: string) {
    const g = group(id)
    if (g && title.trim()) {
      g.title = title.trim().slice(0, 40)
      save()
    }
  }
  function removeGroup(id: string) {
    if (!doc.value || doc.value.groups.length <= 1) return
    doc.value.groups = doc.value.groups.filter((g) => g.id !== id)
    save()
  }
  function moveGroup(id: string, delta: number) {
    const gs = doc.value?.groups
    if (!gs) return
    const i = gs.findIndex((g) => g.id === id)
    const j = i + delta
    if (i < 0 || j < 0 || j >= gs.length) return
    ;[gs[i], gs[j]] = [gs[j]!, gs[i]!]
    save()
  }

  // ----- Lignes -----
  function addRow(groupId: string) {
    group(groupId)?.rows.push({ id: rid('r'), tiles: [] })
    save()
  }
  function removeRow(groupId: string, rowId: string) {
    const g = group(groupId)
    if (!g) return
    g.rows = g.rows.filter((r) => r.id !== rowId)
    save()
  }
  function moveRow(groupId: string, rowId: string, delta: number) {
    const rows = group(groupId)?.rows
    if (!rows) return
    const i = rows.findIndex((r) => r.id === rowId)
    const j = i + delta
    if (i < 0 || j < 0 || j >= rows.length) return
    ;[rows[i], rows[j]] = [rows[j]!, rows[i]!]
    save()
  }

  // ----- Tuiles -----
  function addTile(groupId: string, rowId: string, tile: Omit<CockpitTile, 'id'>) {
    group(groupId)
      ?.rows.find((r) => r.id === rowId)
      ?.tiles.push({ ...tile, id: rid('t') })
    save()
  }
  function updateTile(tileId: string, patch: Partial<Omit<CockpitTile, 'id'>>) {
    const found = findTile(tileId)
    if (!found) return
    Object.assign(found.tile, patch)
    save()
  }
  function removeTile(tileId: string) {
    const found = findTile(tileId)
    if (!found) return
    found.row.tiles = found.row.tiles.filter((t) => t.id !== tileId)
    save()
  }
  /** Changement de groupe : uniquement par cette action explicite (jamais par glisser-déposer). */
  function moveTileToGroup(tileId: string, groupId: string) {
    const found = findTile(tileId)
    const target = group(groupId)
    if (!found || !target || found.group.id === groupId) return
    found.row.tiles = found.row.tiles.filter((t) => t.id !== tileId)
    if (!target.rows.length) target.rows.push({ id: rid('r'), tiles: [] })
    target.rows[target.rows.length - 1]!.tiles.push(found.tile)
    save()
  }

  async function reset() {
    const res = await api<{ revision: number; document: CockpitDocument }>('/api/v1/cockpit/layout/reset', { method: 'POST' })
    doc.value = res.document
    revision.value = res.revision
    status.value = 'saved'
  }

  async function importDocument(document: unknown) {
    const res = await api<{ revision: number; document: CockpitDocument }>('/api/v1/cockpit/layout/import', { method: 'POST', json: document })
    doc.value = res.document
    revision.value = res.revision
  }

  return {
    doc,
    revision,
    status,
    error,
    editing,
    snapshots,
    snapshotsError,
    alerts,
    alertsLoaded,
    resolved,
    tasks,
    setOnDemand,
    anyDemo,
    overview,
    load,
    loadSnapshots,
    snapshot,
    guest,
    flush,
    save,
    group,
    addGroup,
    renameGroup,
    removeGroup,
    moveGroup,
    addRow,
    removeRow,
    moveRow,
    addTile,
    updateTile,
    removeTile,
    moveTileToGroup,
    reset,
    importDocument,
  }
})
