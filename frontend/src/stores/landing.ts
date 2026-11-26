import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, ApiError } from '@/api/client'
import type { LandingDocument, LayoutResponse, Widget, WidgetType } from '@/api/types'
import { randomHex } from '@/design-system/id'
import { type Breakpoint, type Item, mobileOrder } from '@/spaces/landing/grid'

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error' | 'conflict'

const DEFAULT_CONFIG: Record<WidgetType, Record<string, unknown>> = {
  search: {},
  weather: { label: '', latitude: null, longitude: null, forecast_days: 5 },
  calendar: { source_ids: null, days_ahead: 7, max_events: 6 },
  news: { category_ids: null, count: 9 },
  todo: { shape: 'square' },
  note: {},
}

function newId(): string {
  return `w_${randomHex()}`
}

export const useLanding = defineStore('landing', () => {
  const doc = ref<LandingDocument | null>(null)
  const revision = ref(0)
  const status = ref<SaveStatus>('idle')
  const error = ref('')
  const editing = ref(false)
  let timer: number | undefined
  let inflight: Promise<void> | null = null

  const widgets = computed(() => doc.value?.widgets ?? [])
  const hidden = computed(() => widgets.value.filter((w) => w.hidden))

  function set(res: LayoutResponse) {
    doc.value = res.document
    revision.value = res.revision
  }

  async function load() {
    set(await api<LayoutResponse>('/api/v1/landing/layout'))
  }

  async function flush() {
    if (!doc.value) return
    window.clearTimeout(timer)
    if (inflight) await inflight
    status.value = 'saving'
    inflight = (async () => {
      try {
        const res = await api<LayoutResponse>('/api/v1/landing/layout', {
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

  /** Enregistrement automatique (anti-rebond 800 ms). */
  function scheduleSave() {
    status.value = 'saving'
    window.clearTimeout(timer)
    timer = window.setTimeout(() => void flush(), 800)
  }

  function widget(id: string): Widget | undefined {
    return doc.value?.widgets.find((w) => w.id === id)
  }

  function commitGrid(bp: Exclude<Breakpoint, 'mobile'>, items: Item[]) {
    for (const it of items) {
      const w = widget(it.id)
      if (w) w.placement[bp] = { x: it.x, y: it.y, w: it.w, h: it.h }
    }
    scheduleSave()
  }

  function commitMobile(items: Item[]) {
    if (!doc.value) return
    const sorted = [...items].sort((a, b) => a.y - b.y)
    doc.value.mobile = { mode: 'custom', order: sorted.map((i) => i.id) }
    for (const it of items) {
      const w = widget(it.id)
      if (w) w.placement.mobile_h = it.h
    }
    scheduleSave()
  }

  function addWidget(type: WidgetType): string {
    const id = newId()
    doc.value?.widgets.push({
      id,
      type,
      title: null,
      hidden: false,
      config: structuredClone(DEFAULT_CONFIG[type]),
      placement: { desktop: null, tablet: null, mobile_h: null },
    })
    if (doc.value?.mobile.mode === 'custom') doc.value.mobile.order.push(id)
    scheduleSave()
    return id
  }

  function removeWidget(id: string) {
    if (!doc.value) return
    // Le contenu d'un widget Tâches ou Post-it est supprimé avec lui (suppression confirmée dans l'éditeur)
    const type = widget(id)?.type
    if (type === 'todo') void api(`/api/v1/todo?widget=${id}`, { method: 'DELETE' }).catch(() => {})
    if (type === 'note') void api(`/api/v1/notes?widget=${id}`, { method: 'DELETE' }).catch(() => {})
    doc.value.widgets = doc.value.widgets.filter((w) => w.id !== id)
    doc.value.mobile.order = doc.value.mobile.order.filter((i) => i !== id)
    scheduleSave()
  }

  function setHidden(id: string, value: boolean) {
    const w = widget(id)
    if (!w) return
    w.hidden = value
    if (!value) w.placement.desktop = w.placement.tablet = null // réapparaît à la première place libre
    scheduleSave()
  }

  function updateWidget(id: string, patch: { title?: string | null; config?: Record<string, unknown> }) {
    const w = widget(id)
    if (!w) return
    if (patch.title !== undefined) w.title = patch.title || null
    if (patch.config) w.config = { ...w.config, ...patch.config }
    scheduleSave()
  }

  function resetMobile() {
    if (!doc.value) return
    doc.value.mobile = { mode: 'auto', order: [] }
    for (const w of doc.value.widgets) w.placement.mobile_h = null
    scheduleSave()
  }

  async function reset() {
    set(await api<LayoutResponse>('/api/v1/landing/layout/reset', { method: 'POST' }))
    status.value = 'saved'
  }

  async function importDocument(document: unknown) {
    set(await api<LayoutResponse>('/api/v1/landing/layout/import', { method: 'POST', json: document }))
    status.value = 'saved'
  }

  const currentMobileOrder = computed(() => (doc.value ? mobileOrder(doc.value) : []))

  return {
    doc,
    revision,
    status,
    error,
    editing,
    widgets,
    hidden,
    load,
    flush,
    widget,
    commitGrid,
    commitMobile,
    addWidget,
    removeWidget,
    setHidden,
    updateWidget,
    resetMobile,
    reset,
    importDocument,
    currentMobileOrder,
  }
})
