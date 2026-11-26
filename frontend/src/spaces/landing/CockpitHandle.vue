<script setup lang="ts">
import { PhCaretDown } from '@phosphor-icons/vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { navigateInstant } from '@/app/transition'
import { usePolling } from '@/design-system/usePolling'
import DemoBadge from '@/spaces/cockpit/DemoBadge.vue'
import { useCockpit } from '@/stores/cockpit'

const router = useRouter()
const cockpit = useCockpit()
// État de l'infrastructure : mêmes données que le Cockpit (store partagé), donc déjà prêtes à son ouverture
usePolling(() => cockpit.loadSnapshots(), 30_000)
const connectors = computed(() => cockpit.snapshots.length)
const demo = computed(() => cockpit.snapshots.some((x) => x.demo))
const status = computed(() => (connectors.value && cockpit.alertsLoaded ? cockpit.alerts.length : null))

/** Précharge le code et la disposition du Cockpit : l'ouverture est alors immédiate. */
let prefetched = false
function prefetch() {
  if (prefetched) return
  prefetched = true
  void import('@/spaces/cockpit/CockpitPage.vue')
  if (!cockpit.doc) void cockpit.load().catch(() => (prefetched = false))
}
// Fixé en bas de l'écran : quand la page défile, seuls le chevron et l'alerte restent (« stuck »)
// Calcul sur la hauteur *complète* de la page (texte compris) : pas d'oscillation à la limite
const wrap = ref<HTMLElement>()
const labelEl = ref<HTMLElement>()
const stuck = ref(false)
let labelH = 0
let ro: ResizeObserver | undefined
function measure() {
  if (!stuck.value && labelEl.value) labelH = labelEl.value.offsetHeight + 10 // + écart de la grille
  const full = document.documentElement.scrollHeight + (stuck.value ? labelH : 0)
  stuck.value = full > window.innerHeight + 1
}
onMounted(() => {
  measure()
  ro = new ResizeObserver(measure)
  const page = wrap.value?.parentElement
  if (page) ro.observe(page)
  window.addEventListener('resize', measure, { passive: true })
})
onBeforeUnmount(() => {
  ro?.disconnect()
  window.removeEventListener('resize', measure)
})
onMounted(() => {
  if ('requestIdleCallback' in window) window.requestIdleCallback(prefetch, { timeout: 400 })
  else setTimeout(prefetch, 200)
})
const go = () => void navigateInstant(router, '/cockpit')
</script>

<template>
  <div ref="wrap" class="handle-wrap" :class="{ stuck }">
    <button class="handle glass" type="button" aria-describedby="cockpit-hint" @pointerenter="prefetch" @focus="prefetch" @click="go">
      <PhCaretDown :size="22" weight="bold" />
      <span class="sr-only">{{ $t('Accéder au cockpit') }}</span>
    </button>
    <p id="cockpit-hint" ref="labelEl" class="label">
      <strong>{{ $t('Accéder au cockpit') }}</strong>
      <span class="muted">{{ $t('Infrastructure · Services · Supervision') }}</span>
    </p>
    <button
      v-if="status !== null"
      type="button"
      class="state glass"
      :class="{ alert: status > 0 }"
      :aria-label="status ? $tn(status, '{n} alerte dans le cockpit : afficher', '{n} alertes dans le cockpit : afficher') : $t('Aucun problème détecté')"
      @click="go"
    >
      <span v-if="status" class="count">{{ status > 99 ? '99+' : status }}</span>
      <span v-else class="dot ok" />
      {{ status ? (status > 1 ? $t('Alertes') : $t('Alerte')) : $t('Aucun problème détecté') }}
      <DemoBadge v-if="demo" class="demo" />
    </button>
  </div>
</template>

<style scoped>
.handle-wrap {
  position: sticky;
  bottom: 0;
  z-index: 30;
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 22px 0 calc(24px + env(safe-area-inset-bottom));
  pointer-events: none; /* les tuiles restent cliquables autour */
}
.handle-wrap > * {
  pointer-events: auto;
}
.handle-wrap.stuck {
  background: linear-gradient(to top, rgb(var(--surface-rgb) / 0.55) 20%, transparent);
}
/* Collé en bas : chevron + alerte seulement (le texte reste lisible pour les lecteurs d'écran) */
.handle-wrap.stuck .label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}
.handle {
  width: 58px;
  height: 58px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  padding: 0;
  color: var(--text-1);
  transition: transform var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
  animation: breathe 3.2s var(--ease) infinite;
}
.handle:hover {
  transform: translateY(2px);
  box-shadow: var(--shadow-float);
}
.handle:focus-visible {
  border-radius: 50%;
}
@keyframes breathe {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(3px);
  }
}
.label {
  margin: 0;
  display: grid;
  justify-items: center;
  gap: 2px;
  font-size: 15px;
}
.label .muted {
  font-size: 13px;
}
.state {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 14px 0 12px;
  border-radius: var(--radius-pill);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-1);
  white-space: nowrap;
  cursor: pointer;
}
.demo {
  height: 17px;
  font-size: 9.5px;
  margin-right: -6px;
}
.state.alert {
  padding-left: 5px;
}
.count {
  min-width: 22px;
  height: 22px;
  padding: 0 5px;
  border-radius: var(--radius-pill);
  background: var(--down);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 11.5px;
  font-weight: 700;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--down) 25%, transparent);
}
</style>
