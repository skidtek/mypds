<script setup lang="ts">
import { serverText } from '@/i18n/server'
import { PhArrowDown, PhArrowUp, PhDesktop, PhShieldCheck, PhWifiHigh } from '@phosphor-icons/vue'
import { computed } from 'vue'
import type { CockpitTile, UnifiData } from '@/api/types'
import { hhmm } from '@/design-system/time'
import { useCockpit } from '@/stores/cockpit'
import DemoBadge from '../DemoBadge.vue'
import { bitrate, uptime } from '../format'
import Gauge from '../Gauge.vue'
import TileIcon from '../TileIcon.vue'

const props = defineProps<{ tile: CockpitTile }>()
const store = useCockpit()
const snap = computed(() => store.snapshot(props.tile.config.connector_id))
const d = computed(() => snap.value?.data as unknown as UnifiData | null | undefined)
const gw = computed(() => d.value?.gateway ?? null)
const health = computed(() => (!gw.value ? '' : !gw.value.online ? 'down' : d.value!.counts.offline ? 'warn' : 'ok'))
</script>

<template>
  <div class="sum">
    <header class="head">
      <TileIcon :icon="{ kind: 'simple', value: 'ubiquiti' }" :size="36" />
      <div class="ttl">
        <h3>{{ gw?.name ?? snap?.name ?? 'UniFi' }}</h3>
        <span class="faint">{{ gw?.model ?? 'UniFi Network' }}<template v-if="d"> · {{ $t('site « {name} »', { name: d.site.name }) }}</template></span>
      </div>
      <DemoBadge v-if="snap?.demo" />
      <span v-if="snap?.fetched_at" class="faint when">{{ hhmm(snap.fetched_at) }}</span>
    </header>

    <p v-if="!snap" class="empty">{{ $t('Connecteur introuvable ou désactivé.') }}</p>
    <p v-else-if="!d" class="empty"><span class="dot" /> {{ snap.error ? $t('Données indisponibles : {error}', { error: serverText(snap.error) }) : $t('Données indisponibles') }}</p>
    <div v-else class="body">
      <section class="block net">
        <h4>{{ $t('Internet') }}</h4>
        <p class="state"><span class="dot big" :class="health" /> {{ gw?.online ? $t('En ligne') : gw ? $t('Hors ligne') : $t('Pas de passerelle') }}</p>
        <div v-if="d.wan" class="rates">
          <span :title="$t('Réception (débit actuel)')"><PhArrowDown :size="15" weight="bold" class="down" /> {{ bitrate(d.wan.down_bps) }}</span>
          <span :title="$t('Envoi (débit actuel)')"><PhArrowUp :size="15" weight="bold" class="up" /> {{ bitrate(d.wan.up_bps) }}</span>
        </div>
        <p v-if="gw?.uptime_s" class="faint small">{{ $t('Allumée depuis {d}', { d: uptime(gw.uptime_s) }) }}</p>
      </section>
      <section class="block">
        <h4>{{ $t('Équipements') }}</h4>
        <p class="big-num">{{ d.counts.online }}<small>/{{ d.counts.devices }}</small></p>
        <p class="muted small">
          {{ $t('en ligne') }}<template v-if="d.counts.offline"> · <span class="bad">{{ $tn(d.counts.offline, '{n} hors ligne', '{n} hors ligne') }}</span></template>
        </p>
        <p v-if="d.counts.updates" class="upd small">{{ $tn(d.counts.updates, '{n} mise à jour disponible', '{n} mises à jour disponibles') }}</p>
      </section>
      <section class="block">
        <h4>{{ $t('Clients') }}</h4>
        <p class="big-num">{{ d.clients.total }}</p>
        <p class="kinds small">
          <span :title="$t('Wi-Fi')"><PhWifiHigh :size="14" /> {{ d.clients.wireless }}</span>
          <span :title="$t('Filaire')"><PhDesktop :size="14" /> {{ d.clients.wired }}</span>
          <span v-if="d.clients.vpn" :title="$t('VPN')"><PhShieldCheck :size="14" /> {{ d.clients.vpn }}</span>
        </p>
      </section>
      <section v-if="gw && (gw.cpu_pct != null || gw.mem_pct != null)" class="block res">
        <Gauge :value="gw.cpu_pct == null ? null : gw.cpu_pct / 100" label="CPU" :detail="$t('Passerelle')" />
        <Gauge :value="gw.mem_pct == null ? null : gw.mem_pct / 100" :label="$t('Mémoire')" :detail="$t('Passerelle')" />
      </section>
    </div>
    <p v-if="d" class="faint note">{{ $t('Test de débit, latence et fournisseur d\'accès : non disponibles via l\'API officielle UniFi.') }}</p>
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
  grid-template-columns: 1.3fr 1fr 1fr 1.6fr;
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
.rates {
  display: flex;
  gap: 16px;
  margin-top: 10px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}
.rates span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.down {
  color: #34c759;
}
.up {
  color: #0a84ff;
}
.big-num {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.big-num small {
  font-size: 15px;
  color: var(--text-3);
}
.small {
  margin: 6px 0 0;
  font-size: 12.5px;
}
.bad {
  color: var(--down);
  font-weight: 600;
}
.upd {
  color: var(--accent);
  font-weight: 600;
}
.kinds {
  display: flex;
  gap: 12px;
}
.kinds span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.res {
  display: flex;
  justify-content: space-around;
  align-items: center;
  gap: 8px;
}
.note {
  margin: 0;
  font-size: 11.5px;
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
