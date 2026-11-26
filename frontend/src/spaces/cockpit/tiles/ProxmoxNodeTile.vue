<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { CockpitTile, HistoryPoint } from '@/api/types'
import { useCockpit } from '@/stores/cockpit'
import DemoBadge from '../DemoBadge.vue'
import { bytes, level, pct, ratio, uptime } from '../format'
import { history } from '../history'
import Sparkline from '../Sparkline.vue'
import TileIcon from '../TileIcon.vue'
import { t } from '@/i18n'

const props = defineProps<{ tile: CockpitTile }>()
const store = useCockpit()
const snap = computed(() => store.snapshot(props.tile.config.connector_id))
const node = computed(() => snap.value?.data?.nodes.find((n) => n.name === props.tile.config.node))
const points = ref<HistoryPoint[]>([])

watch(
  () => [snap.value?.fetched_at, props.tile.config.node],
  async () => {
    if (!props.tile.config.connector_id || !props.tile.config.node || !node.value?.online) return
    try {
      points.value = await history(props.tile.config.connector_id, `node/${props.tile.config.node}`)
    } catch {
      points.value = []
    }
  },
  { immediate: true },
)

const bars = computed(() => {
  const n = node.value
  if (!n) return []
  return [
    { label: 'CPU', v: n.cpu, detail: t('{n} cœurs', { n: n.maxcpu ?? '?' }) },
    { label: t('Mémoire'), v: ratio(n.mem, n.maxmem), detail: `${bytes(n.mem)} / ${bytes(n.maxmem)}` },
    { label: t('Disque'), v: ratio(n.disk, n.maxdisk), detail: `${bytes(n.disk)} / ${bytes(n.maxdisk)}` },
  ]
})
</script>

<template>
  <div class="node">
    <header class="head">
      <TileIcon fallback="node" :size="36" />
      <div class="ttl">
        <h3>{{ tile.config.node }}</h3>
        <span class="faint">{{ node?.ip ?? $t('Nœud Proxmox') }}</span>
      </div>
      <DemoBadge v-if="snap?.demo" />
      <span class="dot" :class="{ ok: node?.online, down: node && !node.online }" :title="node ? (node.online ? $t('En ligne') : $t('Hors ligne')) : $t('Inconnu')" />
    </header>
    <p v-if="!node" class="empty">{{ snap?.data ? $t('Nœud introuvable dans le cluster.') : $t('Données indisponibles.') }}</p>
    <p v-else-if="!node.online" class="empty">{{ $t('Nœud hors ligne.') }}</p>
    <template v-else>
      <ul class="bars">
        <li v-for="b in bars" :key="b.label">
          <span class="lbl">{{ b.label }}</span>
          <span class="track"><span class="fill" :class="level(b.v)" :style="{ width: `${Math.round((b.v ?? 0) * 100)}%` }" /></span>
          <span class="val">{{ pct(b.v) }}</span>
        </li>
      </ul>
      <Sparkline v-if="points.length" class="spark" :values="points.map((p) => p.cpu)" :max="0.25" />
      <footer class="faint">
        <span>{{ node.vms }} VM · {{ node.lxcs }} LXC</span>
        <span>{{ $t('Actif depuis {d}', { d: uptime(node.uptime) }) }}</span>
      </footer>
    </template>
  </div>
</template>

<style scoped>
.node {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
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
  font-size: 16px;
  font-weight: 680;
}
.ttl .faint {
  font-size: 12.5px;
}
.bars {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 9px;
}
.bars li {
  display: grid;
  grid-template-columns: 64px 1fr 46px;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}
.lbl {
  color: var(--text-2);
}
.track {
  height: 7px;
  border-radius: 4px;
  background: var(--hairline);
  overflow: hidden;
}
.fill {
  display: block;
  height: 100%;
  border-radius: 4px;
  background: var(--accent);
  transition: width var(--dur-slow) var(--ease);
}
.fill.warn {
  background: var(--warn);
}
.fill.down {
  background: var(--down);
}
.val {
  text-align: right;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}
.spark {
  margin-top: auto;
}
footer {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
}
.empty {
  margin: auto 0;
  color: var(--text-2);
  font-size: 14px;
}
</style>
