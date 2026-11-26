<script setup lang="ts">
import { serverText } from '@/i18n/server'
import { computed } from 'vue'
import type { CockpitTile, DockerData } from '@/api/types'
import { hhmm } from '@/design-system/time'
import { useCockpit } from '@/stores/cockpit'
import DemoBadge from '../DemoBadge.vue'
import { bytes } from '../format'
import TileIcon from '../TileIcon.vue'
import { t } from '@/i18n'

const props = defineProps<{ tile: CockpitTile }>()
const store = useCockpit()
const snap = computed(() => store.snapshot(props.tile.config.connector_id))
const d = computed(() => snap.value?.data as unknown as DockerData | null | undefined)
const problems = computed(() =>
  (d.value?.containers ?? []).filter((c) => (['exited', 'dead'].includes(c.state) && !c.on_demand) || c.health === 'unhealthy' || c.state === 'restarting'),
)
const health = computed(() => (!d.value ? '' : problems.value.length ? 'warn' : 'ok'))
const why = (c: DockerData['containers'][number]) =>
  c.state === 'restarting' ? t('redémarre en boucle') : c.health === 'unhealthy' ? t('mauvaise santé') : t('arrêté (code {code})', { code: c.exit_code ?? '?' })
const top = computed(() =>
  [...(d.value?.containers ?? [])].filter((c) => c.cpu_pct != null).sort((a, b) => (b.cpu_pct ?? 0) - (a.cpu_pct ?? 0)).slice(0, 3),
)
</script>

<template>
  <div class="sum">
    <header class="head">
      <TileIcon :icon="{ kind: 'simple', value: 'docker' }" :size="36" />
      <div class="ttl">
        <h3>{{ d?.host.name ?? snap?.name ?? 'Docker' }}</h3>
        <span class="faint">Docker {{ d?.host.docker_version ?? '' }}<template v-if="d?.host.os"> · {{ d.host.os }}</template></span>
      </div>
      <DemoBadge v-if="snap?.demo" />
      <span v-if="snap?.fetched_at" class="faint when">{{ hhmm(snap.fetched_at) }}</span>
    </header>

    <p v-if="!snap" class="empty">{{ $t('Connecteur introuvable ou désactivé.') }}</p>
    <p v-else-if="!d" class="empty"><span class="dot" /> {{ snap.error ? $t('Données indisponibles : {error}', { error: serverText(snap.error) }) : $t('Données indisponibles') }}</p>
    <div v-else class="body">
      <section class="block">
        <h4>{{ $t('Conteneurs') }}</h4>
        <p class="state"><span class="dot big" :class="health" /> {{ d.counts.running }}<small>/{{ d.counts.total }}</small></p>
        <p class="muted small">{{ $t('en marche') }}<template v-if="d.counts.stopped"> · {{ $tn(d.counts.stopped, '{n} arrêté', '{n} arrêtés') }}</template></p>
      </section>
      <section class="block">
        <h4>{{ $t('À surveiller') }}</h4>
        <ul v-if="problems.length" class="list">
          <li v-for="c in problems.slice(0, 4)" :key="c.id"><span class="dot" :class="c.state === 'running' ? 'warn' : 'down'" /> <span class="n">{{ c.name }}</span> <span class="faint">{{ why(c) }}</span></li>
          <li v-if="problems.length > 4" class="faint">{{ $t('et {n} autres', { n: problems.length - 4 }) }}</li>
        </ul>
        <p v-else class="muted small"><span class="dot ok" /> {{ $t('Aucun problème détecté') }}</p>
      </section>
      <section class="block">
        <h4>{{ $t('Plus actifs') }}</h4>
        <ul class="list">
          <li v-for="c in top" :key="c.id"><span class="n">{{ c.name }}</span> <span class="faint num">{{ c.cpu_pct?.toLocaleString() }} % · {{ bytes(c.mem_used) }}</span></li>
        </ul>
      </section>
      <section class="block">
        <h4>{{ $t('Hôte') }}</h4>
        <dl>
          <dt>CPU</dt>
          <dd>{{ $t('{n} cœurs', { n: d.host.cpus ?? '?' }) }}</dd>
          <dt>{{ $t('Mémoire') }}</dt>
          <dd>{{ bytes(d.host.mem_total) }}</dd>
          <dt>{{ $t('Images') }}</dt>
          <dd>{{ d.host.images ?? '—' }}</dd>
        </dl>
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
.body {
  display: grid;
  grid-template-columns: 1fr 1.6fr 1.4fr 1fr;
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
  font-size: 26px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.state small {
  font-size: 15px;
  color: var(--text-3);
  margin-left: -8px;
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
  gap: 6px;
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
  font-size: 13px;
}
.list li {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.n {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.list .faint {
  margin-left: auto;
  white-space: nowrap;
  font-size: 12px;
}
.num {
  font-variant-numeric: tabular-nums;
}
dl {
  margin: 0;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 12px;
  font-size: 13px;
}
dt {
  color: var(--text-2);
}
dd {
  margin: 0;
  text-align: right;
  font-weight: 650;
}
.empty {
  margin: auto 0;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-2);
  font-size: 14px;
}
@container (max-width: 760px) {
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
