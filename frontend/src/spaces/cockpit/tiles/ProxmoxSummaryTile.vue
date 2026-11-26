<script setup lang="ts">
import { serverText } from '@/i18n/server'
import { computed } from 'vue'
import type { CockpitTile } from '@/api/types'
import { hhmm } from '@/design-system/time'
import { useCockpit } from '@/stores/cockpit'
import DemoBadge from '../DemoBadge.vue'
import { bytes } from '../format'
import Gauge from '../Gauge.vue'
import TileIcon from '../TileIcon.vue'
import { tk } from '@/i18n'

const props = defineProps<{ tile: CockpitTile }>()
const store = useCockpit()
const snap = computed(() => store.snapshot(props.tile.config.connector_id))
const d = computed(() => snap.value?.data)
const HEALTH = { ok: tk('Opérationnel'), warning: tk('Dégradé'), down: tk('Hors service'), unknown: tk('Inconnu') } as const
const dot = computed(() => ({ ok: 'ok', warning: 'warn', down: 'down', unknown: '' })[d.value?.cluster.health ?? 'unknown'])
</script>

<template>
  <div class="sum">
    <header class="head">
      <TileIcon :icon="{ kind: 'simple', value: 'proxmox' }" :size="36" />
      <div class="ttl">
        <h3>{{ d?.cluster.name ?? snap?.name ?? 'Proxmox' }}</h3>
        <span class="faint">{{ d?.cluster.standalone ? $t('Nœud Proxmox VE') : $t('Cluster Proxmox VE') }}</span>
      </div>
      <DemoBadge v-if="snap?.demo" />
      <span v-if="snap?.fetched_at" class="faint when">{{ hhmm(snap.fetched_at) }}</span>
    </header>

    <p v-if="!snap" class="empty">{{ $t('Connecteur introuvable ou désactivé.') }}</p>
    <p v-else-if="!d" class="empty"><span class="dot" /> {{ snap.error ? $t('Données indisponibles : {error}', { error: serverText(snap.error) }) : $t('Données indisponibles') }}</p>
    <div v-else class="body">
      <section class="block health">
        <h4>{{ $t('État') }}</h4>
        <p class="state"><span class="dot big" :class="dot" /> {{ $t(HEALTH[d.cluster.health]) }}</p>
        <p class="muted">
          <template v-if="!d.cluster.standalone">{{ d.cluster.quorate ? $t('Quorum OK') : $t('Quorum perdu') }} · </template>
          {{ $tn(d.cluster.nodes_total, '{on}/{n} nœud en ligne', '{on}/{n} nœuds en ligne', { on: d.cluster.nodes_online }) }}
        </p>
      </section>
      <section class="block guests">
        <h4>{{ $t('Invités') }}</h4>
        <dl>
          <dt>{{ $t('Machines virtuelles') }}</dt>
          <dd><span class="dot ok" /> {{ d.guests.vm_running }} <span class="dot" /> {{ d.guests.vm_stopped }}</dd>
          <dt>{{ $t('Conteneurs LXC') }}</dt>
          <dd><span class="dot ok" /> {{ d.guests.lxc_running }} <span class="dot" /> {{ d.guests.lxc_stopped }}</dd>
        </dl>
        <p class="faint legend">{{ $t('en marche · arrêtés') }}</p>
      </section>
      <section class="block res">
        <Gauge :value="d.resources.cpu" label="CPU" :detail="$t('{n} cœurs', { n: d.resources.cpus })" />
        <Gauge :value="d.resources.mem" :label="$t('Mémoire')" :detail="`${bytes(d.resources.mem_used)} / ${bytes(d.resources.mem_total)}`" />
        <Gauge :value="d.resources.disk" :label="$t('Stockage')" :detail="`${bytes(d.resources.disk_used)} / ${bytes(d.resources.disk_total)}`" />
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
  grid-template-columns: 1fr 1fr 2.2fr;
  gap: 14px;
  align-items: stretch;
}
.block {
  border-radius: var(--radius-md);
  background: rgb(var(--surface-rgb) / 0.35);
  border: 1px solid var(--hairline);
  padding: 14px 16px;
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
.health .muted {
  margin: 8px 0 0;
  font-size: 13px;
}
.dot.big {
  width: 14px;
  height: 14px;
}
.dot.warn {
  background: var(--warn);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--warn) 22%, transparent);
}
dl {
  margin: 0;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px 12px;
  font-size: 13.5px;
}
dt {
  color: var(--text-2);
}
dd {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}
.legend {
  margin: 8px 0 0;
  font-size: 11.5px;
}
.res {
  display: flex;
  justify-content: space-around;
  align-items: center;
  gap: 8px;
  padding-top: 18px;
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
  .res {
    grid-column: 1 / -1;
  }
}
@container (max-width: 420px) {
  .body {
    grid-template-columns: 1fr;
  }
  .res {
    flex-wrap: wrap;
  }
}
</style>
