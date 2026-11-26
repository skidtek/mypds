<script setup lang="ts">
import { PhBell, PhCheckCircle, PhEyeSlash, PhWarning, PhWarningOctagon } from '@phosphor-icons/vue'
import { computed, ref } from 'vue'
import { since } from '@/design-system/time'
import { useCockpit } from '@/stores/cockpit'
import { useSession } from '@/stores/session'
import DemoBadge from '../DemoBadge.vue'
import { t } from '@/i18n'
import { alertDetail, alertTitle } from '../labels'

defineProps<{ editing: boolean }>()
const store = useCockpit()
const session = useSession()
const busy = ref<string | null>(null)
const error = ref('')

/** Bonnes nouvelles : dernière sauvegarde réussie de chaque invité (24 h). */
const goodNews = computed(() => {
  const seen = new Set<string>()
  const out: { key: string; text: string; at: number }[] = []
  const dayAgo = Date.now() / 1000 - 86400
  for (const t2 of store.tasks) {
    if (t2.type !== 'vzdump' || !t2.end || seen.has(t2.target)) continue
    seen.add(t2.target)
    if (t2.state === 'ok' && t2.end >= dayAgo) out.push({ key: t2.upid, text: t('Sauvegarde de {name} : OK', { name: t2.target_name || t2.target }), at: t2.end })
  }
  return out.slice(0, 4)
})

async function ignore(a: (typeof store.alerts)[number]) {
  if (!a.resource) return
  busy.value = a.id
  error.value = ''
  try {
    await store.setOnDemand(a.connector_id, a.resource, true)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <div class="alerts">
    <header class="head">
      <PhBell :size="20" />
      <h3>{{ $t('Alertes & notifications') }}</h3>
      <span v-if="store.alerts.length" class="count" :aria-label="$tn(store.alerts.length, '{n} alerte active', '{n} alertes actives')">{{ store.alerts.length }}</span>
      <DemoBadge v-if="store.anyDemo" class="badge" />
    </header>

    <ul class="list">
      <li v-for="a in store.alerts" :key="a.id" :class="a.severity">
        <PhWarningOctagon v-if="a.severity === 'critical'" class="ico crit" :size="20" weight="fill" />
        <PhWarning v-else class="ico warn" :size="20" weight="fill" />
        <div class="txt">
          <strong>{{ alertTitle(a) }}</strong>
          <span class="faint">{{ alertDetail(a) ? `${alertDetail(a)} · ` : '' }}{{ since(a.started_at) }}</span>
        </div>
        <button
          v-if="a.kind === 'guest-stopped' && session.me?.role === 'admin' && !editing"
          type="button"
          class="ignore"
          :disabled="busy === a.id"
          :title="$t('Démarrée à la demande : ne plus alerter quand elle est arrêtée')"
          @click="ignore(a)"
        >
          <PhEyeSlash :size="14" /> {{ $t('Ignorer') }}
        </button>
      </li>
      <li v-if="!store.alerts.length" class="ok">
        <PhCheckCircle class="ico okc" :size="20" weight="fill" />
        <div class="txt"><strong>{{ $t('Aucun problème détecté') }}</strong><span class="faint">{{ $tn(store.snapshots.length, 'Surveillance active sur {n} connexion', 'Surveillance active sur {n} connexions') }}</span></div>
      </li>
      <li v-for="n in goodNews" :key="n.key" class="ok">
        <PhCheckCircle class="ico okc" :size="20" weight="fill" />
        <div class="txt"><strong>{{ n.text }}</strong><span class="faint">{{ since(new Date(n.at * 1000).toISOString()) }}</span></div>
      </li>
      <li v-for="r in store.resolved.slice(0, 3)" :key="r.id" class="resolved">
        <PhCheckCircle class="ico" :size="20" />
        <div class="txt"><strong>{{ $t('Résolu : {title}', { title: alertTitle(r) }) }}</strong><span class="faint">{{ r.resolved_at ? since(r.resolved_at) : '' }}</span></div>
      </li>
    </ul>
    <p v-if="error" class="error-text">{{ error }}</p>
  </div>
</template>

<style scoped>
.alerts {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.head {
  display: flex;
  align-items: center;
  gap: 10px;
}
h3 {
  font-size: 16.5px;
  font-weight: 680;
}
.count {
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: var(--radius-pill);
  background: var(--down);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 700;
}
.badge {
  margin-left: auto;
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
  overflow-y: auto;
  max-height: 360px;
  scrollbar-width: thin;
  scrollbar-color: color-mix(in srgb, var(--text-3) 50%, transparent) transparent;
}
.list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: rgb(var(--surface-rgb) / 0.35);
}
.ico {
  flex: none;
}
.crit {
  color: var(--down);
}
.warn {
  color: var(--warn);
}
.okc {
  color: var(--ok);
}
.resolved {
  opacity: 0.65;
}
.resolved .ico {
  color: var(--text-3);
}
.txt {
  display: grid;
  gap: 1px;
  min-width: 0;
  flex: 1;
}
.txt strong {
  font-size: 14px;
  font-weight: 600;
}
.txt .faint {
  font-size: 12.5px;
}
.ignore {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid var(--hairline);
  background: var(--surface-strong);
  border-radius: var(--radius-pill);
  height: 28px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
  flex: none;
}
.ignore:hover {
  color: var(--text-1);
}
</style>
