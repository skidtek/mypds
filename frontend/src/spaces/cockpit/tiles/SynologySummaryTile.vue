<script setup lang="ts">
import { serverText } from '@/i18n/server'
import { PhArrowCircleUp, PhArrowUpRight, PhThermometerSimple } from '@phosphor-icons/vue'
import { computed } from 'vue'
import type { CockpitTile, SynologyData } from '@/api/types'
import { hhmm } from '@/design-system/time'
import { useCockpit } from '@/stores/cockpit'
import DemoBadge from '../DemoBadge.vue'
import { bytesDec } from '../format'
import Gauge from '../Gauge.vue'
import TileIcon from '../TileIcon.vue'
import { t, tk } from '@/i18n'

const props = defineProps<{ tile: CockpitTile; editing: boolean }>()
const store = useCockpit()
const snap = computed(() => store.snapshot(props.tile.config.connector_id))
const d = computed(() => snap.value?.data as unknown as SynologyData | null | undefined)

const hwFault = computed(() => [d.value?.system_ok, d.value?.power_ok, d.value?.fans_ok, d.value?.thermal_ok].some((x) => x === false))
const diskBad = (x: SynologyData['disks'][number]) => ['crashed', 'partition_failed', 'disconnected'].includes(x.status) || ['critical', 'failing'].includes(x.health ?? '')
const diskWarn = (x: SynologyData['disks'][number]) => x.health === 'warning'
const health = computed(() => {
  const v = d.value
  if (!v) return ''
  if (hwFault.value || v.disks.some(diskBad) || v.volumes.some((x) => ['degraded', 'crashed'].includes(x.state))) return 'down'
  if (v.disks.some(diskWarn) || v.volumes.some((x) => x.state === 'busy')) return 'warn'
  return 'ok'
})
const HEALTH = { ok: tk('Opérationnel'), warn: tk('À surveiller'), down: tk('Anomalie') } as Record<string, string>
const VOL = { normal: tk('Normal'), degraded: tk('Dégradé'), crashed: tk('En panne'), busy: tk('Opération en cours'), unknown: tk('Inconnu') } as Record<string, string>
const DISK = { normal: tk('Normal'), warning: tk('Avertissement'), critical: tk('Critique'), failing: tk('Défaillant'), crashed: tk('En panne'),
  partition_failed: tk('Partition système endommagée'), disconnected: tk('Déconnecté'), initialized: tk('Initialisé'), not_initialized: tk('Non initialisé'), unknown: tk('Inconnu') } as Record<string, string>
const diskLabel = (x: SynologyData['disks'][number]) => t(DISK[x.health && x.health !== 'normal' ? x.health : x.status] ?? x.status)
const href = computed(() => (props.editing ? undefined : d.value?.url ?? undefined))
const fmtTime = (s: string | null) => s ?? '—'
</script>

<template>
  <div class="sum">
    <header class="head">
      <TileIcon :icon="{ kind: 'simple', value: 'synology' }" :size="36" />
      <div class="ttl">
        <h3>{{ snap?.name ?? 'Synology' }}</h3>
        <span class="faint">{{ d?.model ?? 'Synology DSM' }}<template v-if="d?.version"> · {{ d.version }}</template></span>
      </div>
      <span v-if="d?.update_available" class="upd"><PhArrowCircleUp :size="15" weight="fill" /> {{ $t('Mise à jour DSM disponible') }}</span>
      <DemoBadge v-if="snap?.demo" />
      <a v-if="href" class="icon-btn" :href="href" target="_blank" rel="noopener noreferrer" :aria-label="$t('Ouvrir DSM')" :title="$t('Ouvrir DSM')"><PhArrowUpRight :size="16" /></a>
      <span v-if="snap?.fetched_at" class="faint when">{{ hhmm(snap.fetched_at) }}</span>
    </header>

    <p v-if="!snap" class="empty">{{ $t('Connecteur introuvable ou désactivé.') }}</p>
    <p v-else-if="!d" class="empty"><span class="dot" /> {{ snap.error ? $t('Données indisponibles : {error}', { error: serverText(snap.error) }) : $t('Données indisponibles') }}</p>
    <div v-else class="body">
      <section class="block">
        <h4>{{ $t('État') }}</h4>
        <p class="state"><span class="dot big" :class="health" /> {{ $t(HEALTH[health] ?? 'Inconnu') }}</p>
        <p v-if="d.temperature != null" class="muted small"><PhThermometerSimple :size="14" /> {{ d.temperature }} °C</p>
        <p v-if="hwFault" class="bad small">{{ $t('Anomalie matérielle (alimentation, ventilateur ou température)') }}</p>
      </section>
      <section class="block vols">
        <h4>{{ $t('Stockage') }}</h4>
        <div v-for="v in d.volumes" :key="v.id" class="vol">
          <div class="vrow">
            <strong>{{ v.name }}</strong>
            <span class="faint">{{ bytesDec(v.used) }} / {{ bytesDec(v.total) }}</span>
          </div>
          <div class="bar" :class="{ warn: (v.pct ?? 0) >= 0.85, down: (v.pct ?? 0) >= 0.95 }"><i :style="{ width: `${Math.round((v.pct ?? 0) * 100)}%` }" /></div>
          <span v-if="v.state !== 'normal'" class="vstate small" :class="{ bad: v.state === 'degraded' || v.state === 'crashed' }">{{ $t(VOL[v.state] ?? v.state) }}</span>
        </div>
      </section>
      <section class="block">
        <h4>{{ $tn(d.disks.length, '{n} disque', '{n} disques') }}</h4>
        <ul class="disks">
          <li v-for="x in d.disks" :key="x.id" :title="`${x.model ?? ''} — ${diskLabel(x)}`">
            <span class="dot" :class="diskBad(x) ? 'down' : diskWarn(x) ? 'warn' : 'ok'" />
            <span class="dn">{{ x.name }}</span>
            <span class="faint">{{ x.temperature != null ? `${x.temperature} °C` : '' }}</span>
            <span v-if="diskBad(x) || diskWarn(x)" class="small bad">{{ diskLabel(x) }}</span>
          </li>
        </ul>
      </section>
      <section class="block">
        <h4>{{ $t('Sauvegardes') }}</h4>
        <template v-if="d.backups?.available">
          <ul class="tasks">
            <li v-for="b in d.backups.tasks" :key="b.name">
              <span class="dot" :class="b.ok === false ? 'down' : b.ok ? 'ok' : ''" />
              <span class="dn">{{ b.name }}</span>
              <span class="faint small">{{ fmtTime(b.last_time) }}</span>
            </li>
            <li v-if="!d.backups.tasks.length" class="faint small">{{ $t('Aucune tâche Hyper Backup.') }}</li>
          </ul>
        </template>
        <p v-else class="faint small">{{ d.backups ? $t('Non disponible : {reason}', { reason: d.backups.reason }) : $t('Non suivies (API DSM désactivée pour cette connexion).') }}</p>
      </section>
      <section v-if="d.cpu_pct != null || d.mem_pct != null" class="block res">
        <Gauge :value="d.cpu_pct == null ? null : d.cpu_pct / 100" label="CPU" />
        <Gauge :value="d.mem_pct == null ? null : d.mem_pct / 100" :label="$t('Mémoire')" />
      </section>
    </div>
  </div>
</template>

<style scoped>
.sum {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
  container-type: inline-size;
}
.head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.ttl {
  display: grid;
  flex: 1;
  min-width: 0;
}
h3 {
  font-size: 17px;
  font-weight: 680;
}
.ttl .faint,
.when {
  font-size: 12.5px;
}
.upd {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--accent);
}
.body {
  display: grid;
  grid-template-columns: 1fr 1.6fr 1.2fr 1.4fr 1.3fr;
  gap: 14px;
}
.block {
  border-radius: var(--radius-md);
  background: rgb(var(--surface-rgb) / 0.35);
  border: 1px solid var(--hairline);
  padding: 14px 16px;
  min-width: 0;
}
h4 {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 650;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-3);
}
.state {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 650;
}
.dot.big {
  width: 14px;
  height: 14px;
}
.dot.warn {
  background: var(--warn);
}
.small {
  margin: 6px 0 0;
  font-size: 12.5px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.bad {
  color: var(--down);
  font-weight: 600;
}
.vols {
  display: grid;
  gap: 10px;
  align-content: start;
}
.vols h4 {
  margin-bottom: 0;
}
.vrow {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
}
.vrow strong {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.vrow .faint {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.bar {
  height: 7px;
  margin-top: 5px;
  border-radius: 999px;
  background: rgb(var(--surface-rgb) / 0.6);
  overflow: hidden;
}
.bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--ok);
}
.bar.warn i {
  background: var(--warn);
}
.bar.down i {
  background: var(--down);
}
.vstate {
  margin-top: 4px;
}
.disks,
.tasks {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
  font-size: 13px;
}
.disks li,
.tasks li {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.dn {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.disks .small,
.tasks .small {
  margin: 0;
}
.res {
  display: flex;
  justify-content: space-around;
  align-items: center;
  gap: 8px;
}
.empty {
  margin: auto 0;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-2);
  font-size: 14px;
}
@container (max-width: 1000px) {
  .body {
    grid-template-columns: 1fr 1fr 1fr;
  }
}
@container (max-width: 640px) {
  .body {
    grid-template-columns: 1fr 1fr;
  }
}
@container (max-width: 420px) {
  .body {
    grid-template-columns: 1fr;
  }
}
</style>
