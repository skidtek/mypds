<script setup lang="ts">
import { PhArrowClockwise, PhCalendarBlank } from '@phosphor-icons/vue'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { CalendarEvent, Widget } from '@/api/types'
import { syncedLabel } from '@/design-system/time'
import { usePolling } from '@/design-system/usePolling'
import WidgetHeader from '../WidgetHeader.vue'
import { intlLocale, t, tn } from '@/i18n'

const props = defineProps<{ widget: Widget; editing: boolean }>()
const router = useRouter()
const events = ref<CalendarEvent[] | null>(null)
const syncedAt = ref<string | null>(null)
const error = ref('')
const hasSources = ref(true)

const cfg = computed(() => props.widget.config as { source_ids: string[] | null; days_ahead: number; max_events: number })

async function load() {
  try {
    const q = new URLSearchParams({ days: String(cfg.value.days_ahead), limit: String(cfg.value.max_events) })
    for (const id of cfg.value.source_ids ?? []) q.append('source_id', id)
    const res = await api<{ events: CalendarEvent[]; synced_at: string | null }>(`/api/v1/calendar/events?${q}`)
    if (!res.events.length && !res.synced_at) {
      hasSources.value = (await api<unknown[]>('/api/v1/calendar/sources')).length > 0
    } else hasSources.value = true
    events.value = res.events
    syncedAt.value = res.synced_at
    error.value = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

const { refresh } = usePolling(load, 5 * 60 * 1000)
watch(cfg, () => void refresh(), { deep: true })

function dayKey(e: CalendarEvent): string {
  return e.all_day ? e.start : new Date(e.start).toLocaleDateString('sv-SE')
}
const todayKey = () => new Date().toLocaleDateString('sv-SE')
const tomorrowKey = () => new Date(Date.now() + 86400000).toLocaleDateString('sv-SE')

function dayLabel(key: string): string {
  if (key <= todayKey()) return t("Aujourd'hui")
  if (key === tomorrowKey()) return t('Demain')
  return new Date(`${key}T12:00:00`).toLocaleDateString(intlLocale.value, { weekday: 'long', day: 'numeric', month: 'short' })
}

const groups = computed(() => {
  const map = new Map<string, CalendarEvent[]>()
  for (const e of events.value ?? []) {
    const k = dayKey(e) < todayKey() ? todayKey() : dayKey(e)
    map.set(k, [...(map.get(k) ?? []), e])
  }
  return [...map.entries()].map(([key, list]) => ({ key, label: dayLabel(key), list }))
})

const todayCount = computed(() => groups.value.find((g) => g.key === todayKey())?.list.length ?? 0)
const subtitle = computed(() => {
  if (!events.value) return ''
  if (todayCount.value === 0) return t("Aujourd'hui · aucun événement")
  return tn(todayCount.value, "Aujourd'hui · {n} événement", "Aujourd'hui · {n} événements")
})

function time(e: CalendarEvent): string {
  if (e.all_day) return t('Journée')
  return new Date(e.start).toLocaleTimeString(intlLocale.value, { hour: '2-digit', minute: '2-digit' })
}

function detail(e: CalendarEvent): string {
  const parts: string[] = []
  if (e.location) parts.push(e.location)
  if (!e.all_day && e.end) {
    const min = Math.round((new Date(e.end).getTime() - new Date(e.start).getTime()) / 60000)
    if (min > 0) parts.push(min % 60 === 0 ? t('{n} h', { n: min / 60 }) : min > 60 ? t('{h} h {m}', { h: Math.floor(min / 60), m: min % 60 }) : t('{n} min', { n: min }))
  }
  return parts.join(' · ')
}

function openSettings() {
  void router.push({ name: 'settings', query: { section: 'agenda' } })
}
</script>

<template>
  <div class="cal">
    <WidgetHeader :title="widget.title || $t('Agenda')" :subtitle="subtitle" :action-label="$t('Gérer les calendriers')" @action="openSettings">
      <template #icon><PhCalendarBlank :size="22" /></template>
    </WidgetHeader>

    <div v-if="error" class="empty">
      <p>{{ $t('Agenda indisponible.') }}<br /><span class="faint">{{ error }}</span></p>
      <button class="btn small" type="button" @click="refresh()"><PhArrowClockwise :size="14" /> {{ $t('Réessayer') }}</button>
    </div>
    <div v-else-if="!hasSources" class="empty">
      <p>{{ $t('Aucun calendrier connecté.') }}</p>
      <button class="btn small" type="button" :disabled="editing" @click="openSettings">{{ $t('Ajouter un calendrier ICS') }}</button>
    </div>
    <div v-else-if="events && !events.length" class="empty">
      <p>{{ $t('Rien de prévu dans les {n} prochains jours.', { n: cfg.days_ahead }) }}</p>
    </div>
    <div v-else-if="events" class="list">
      <section v-for="g in groups" :key="g.key">
        <h4 v-if="groups.length > 1 || g.key !== todayKey()">{{ g.label }}</h4>
        <ul>
          <li v-for="e in g.list" :key="e.id">
            <span class="time">{{ time(e) }}</span>
            <span class="dot" :style="{ background: e.color, boxShadow: `0 0 0 3px ${e.color}33` }" />
            <span class="what">
              <strong>{{ e.title }}</strong>
              <span v-if="detail(e)" class="muted">{{ detail(e) }}</span>
            </span>
          </li>
        </ul>
      </section>
    </div>
    <div v-else class="skeleton" aria-busy="true" :aria-label="$t('Chargement de l\'agenda')" />
    <p v-if="events" class="sync faint">{{ syncedLabel(syncedAt) }}</p>
  </div>
</template>

<style scoped>
.cal {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  container-type: size;
}
.list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  mask-image: linear-gradient(to bottom, #000 85%, transparent);
  padding-bottom: 8px;
}
h4 {
  margin: 6px 0 6px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-3);
}
h4::first-letter {
  text-transform: uppercase;
}
ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}
li {
  display: grid;
  grid-template-columns: 54px 10px 1fr;
  align-items: start;
  gap: 10px;
}
.time {
  font-weight: 650;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}
.dot {
  margin-top: 5px;
}
.what {
  display: grid;
  gap: 1px;
  min-width: 0;
}
.what strong {
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.what .muted {
  font-size: 12.5px;
}
.empty {
  flex: 1;
  display: grid;
  place-content: center;
  justify-items: center;
  text-align: center;
  gap: 10px;
  color: var(--text-2);
  font-size: 14px;
}
.empty p {
  margin: 0;
}
.sync {
  display: none;
  margin: 0;
  font-size: 11.5px;
}
@container (min-height: 300px) {
  .sync {
    display: block;
  }
}
.skeleton {
  flex: 1;
  border-radius: var(--radius-md);
  background: linear-gradient(100deg, transparent 30%, rgb(255 255 255 / 0.25) 50%, transparent 70%) 0 0 / 200% 100%;
  animation: shimmer 1.4s infinite linear;
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}
</style>
