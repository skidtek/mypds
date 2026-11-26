<script setup lang="ts">
import { serverText } from '@/i18n/server'
import { PhArrowCounterClockwise, PhDownloadSimple, PhPlugsConnected, PhUploadSimple } from '@phosphor-icons/vue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { ConnectorSnapshot, DockerData } from '@/api/types'
import { useCockpit } from '@/stores/cockpit'
import { useSession } from '@/stores/session'
import DemoBadge from '@/spaces/cockpit/DemoBadge.vue'
import { t, tk } from '@/i18n'

const store = useCockpit()
const session = useSession()
const router = useRouter()
const isAdmin = computed(() => session.me?.role === 'admin')
const snaps = ref<ConnectorSnapshot[]>([])
/** Services suivis d'une connexion : VM / LXC (Proxmox) ou conteneurs (Docker). */
function services(s: ConnectorSnapshot): { id: string; name: string; sub: string; running: boolean; on_demand: boolean }[] {
  if (!s.data) return []
  if (s.type === 'docker') {
    const cs = (s.data as unknown as DockerData).containers
    return cs.map((c) => ({ id: c.name, name: c.name, sub: c.image ?? '', running: c.state === 'running', on_demand: c.on_demand }))
  }
  return s.data.guest_list.map((g) => ({
    id: g.id,
    name: g.name,
    sub: `${g.type === 'qemu' ? 'VM' : 'LXC'} ${g.vmid} · ${g.node}`,
    running: g.status === 'running',
    on_demand: !!g.on_demand,
  }))
}
const fileInput = ref<HTMLInputElement>()
const message = ref('')
const error = ref('')
const confirmReset = ref(false)
const busy = ref<string | null>(null)

type Thresholds = Record<'cpu_warn' | 'cpu_crit' | 'cpu_minutes' | 'mem_warn' | 'mem_crit' | 'disk_warn' | 'disk_crit', number>
const METRICS = [
  { id: 'cpu', label: tk('Processeur (CPU)') },
  { id: 'mem', label: tk('Mémoire') },
  { id: 'disk', label: tk('Stockage') },
] as const
const thresholds = ref<Thresholds | null>(null)
const thresholdMsg = ref('')

async function loadThresholds() {
  thresholds.value = await api<Thresholds>('/api/v1/alerts/settings')
}
onMounted(loadThresholds)

/** Garde avertissement ≤ critique en déplaçant l'autre curseur, puis enregistre. */
async function saveThresholds(changed: keyof Thresholds) {
  const th = thresholds.value
  if (!th) return
  for (const k of ['cpu', 'mem', 'disk'] as const) {
    if (th[`${k}_warn`] > th[`${k}_crit`]) {
      if (changed === `${k}_warn`) th[`${k}_crit`] = th[`${k}_warn`]
      else th[`${k}_warn`] = th[`${k}_crit`]
    }
  }
  try {
    thresholds.value = await api<Thresholds>('/api/v1/alerts/settings', { method: 'PUT', json: th })
    thresholdMsg.value = t('Seuils enregistrés : pris en compte à la prochaine collecte.')
  } catch (e) {
    thresholdMsg.value = e instanceof Error ? e.message : String(e)
  }
}

async function load() {
  snaps.value = (await api<ConnectorSnapshot[]>('/api/v1/connectors/snapshots')).filter((s) => s.type === 'proxmox' || s.type === 'docker')
}
onMounted(load)

async function importFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  message.value = error.value = ''
  try {
    if (file.size > 512 * 1024) throw new Error(t('Fichier trop volumineux'))
    await store.importDocument(JSON.parse(await file.text()))
    message.value = t('Disposition du Cockpit importée.')
  } catch (err) {
    error.value = err instanceof SyntaxError ? "Ce fichier n'est pas un JSON valide." : err instanceof Error ? err.message : String(err)
  }
}

async function reset() {
  if (!confirmReset.value) {
    confirmReset.value = true
    return
  }
  confirmReset.value = false
  await store.reset()
  message.value = t('Disposition recréée à partir de vos connexions.')
}

async function toggle(connectorId: string, guestId: string, value: boolean) {
  busy.value = `${connectorId}|${guestId}`
  error.value = ''
  try {
    await store.setOnDemand(connectorId, guestId, value)
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <section class="sec">
    <h2>{{ $t('Cockpit') }}</h2>

    <div class="block">
      <h3>{{ $t('Disposition') }}</h3>
      <p class="muted">
        {{ $t('Onglets, lignes et tuiles se modifient directement dans le Cockpit avec le bouton « Modifier le Cockpit ». Ici : sauvegarde, transfert et réinitialisation (sans aucun secret dans le fichier).') }}
      </p>
      <div class="actions">
        <a class="btn" href="/api/v1/cockpit/layout/export" download><PhDownloadSimple :size="16" /> {{ $t('Exporter') }}</a>
        <button class="btn" type="button" @click="fileInput?.click()"><PhUploadSimple :size="16" /> {{ $t('Importer') }}</button>
        <input ref="fileInput" type="file" accept="application/json,.json" hidden @change="importFile" />
        <button class="btn" :class="{ danger: confirmReset }" type="button" @click="reset" @blur="confirmReset = false">
          <PhArrowCounterClockwise :size="16" /> {{ confirmReset ? $t('Confirmer : tout recréer ?') : $t('Réinitialiser') }}
        </button>
      </div>
      <p class="faint hint">{{ $t('Réinitialiser recrée les onglets Accueil, Infrastructure et Services avec vos nœuds et serveurs actuels.') }}</p>
    </div>

    <div class="block">
      <h3>{{ $t('Services démarrés à la demande') }}</h3>
      <p class="muted">
        {{ $t('Un service coché n\'est pas une anomalie quand il est arrêté : pas d\'alerte, pastille grise. Réglage commun à tous les utilisateurs.') }}
      </p>
      <p v-if="!snaps.length" class="faint">{{ $t('Aucune connexion Proxmox ou Docker.') }}</p>
      <div v-for="s in snaps" :key="s.id" class="conn">
        <h4>{{ s.name }} <DemoBadge v-if="s.demo" /></h4>
        <p v-if="!s.data" class="faint">{{ s.error ? $t('Données indisponibles : {error}', { error: serverText(s.error) }) : $t('Données indisponibles.') }}</p>
        <ul v-else class="guests">
          <li v-for="g in services(s)" :key="g.id">
            <span class="dot" :class="g.running ? 'ok' : g.on_demand ? '' : 'down'" />
            <span class="name"><strong>{{ g.name }}</strong> <span class="faint">{{ g.sub }}</span></span>
            <label class="check">
              <input
                type="checkbox"
                :checked="!!g.on_demand"
                :disabled="!isAdmin || busy === `${s.id}|${g.id}`"
                @change="toggle(s.id, g.id, ($event.target as HTMLInputElement).checked)"
              />
              {{ $t('À la demande') }}
            </label>
          </li>
        </ul>
      </div>
      <p v-if="!isAdmin" class="faint hint">{{ $t('Seul un administrateur peut modifier ce réglage.') }}</p>
    </div>

    <div class="block">
      <h3>{{ $t('Seuils d\'alerte') }}</h3>
      <p class="muted">{{ $t('Avertissement (orange) puis critique (rouge), pour chaque nœud et chaque stockage. Réglages communs à tous les utilisateurs.') }}</p>
      <div v-if="thresholds" class="thresholds">
        <fieldset v-for="m in METRICS" :key="m.id" class="metric" :disabled="!isAdmin">
          <legend>{{ $t(m.label) }}</legend>
          <label class="field">
            <span>{{ $t('Avertissement à {n} %', { n: thresholds[`${m.id}_warn`] }) }}</span>
            <input v-model.number="thresholds[`${m.id}_warn`]" type="range" min="70" max="100" @change="saveThresholds(`${m.id}_warn`)" />
          </label>
          <label class="field">
            <span>{{ $t('Critique à {n} %', { n: thresholds[`${m.id}_crit`] }) }}</span>
            <input v-model.number="thresholds[`${m.id}_crit`]" type="range" min="70" max="100" @change="saveThresholds(`${m.id}_crit`)" />
          </label>
          <label v-if="m.id === 'cpu'" class="field">
            <span>{{ $tn(thresholds.cpu_minutes, 'Pendant au moins {n} minute', 'Pendant au moins {n} minutes') }}</span>
            <input v-model.number="thresholds.cpu_minutes" type="range" min="1" max="30" @change="saveThresholds('cpu_minutes')" />
          </label>
        </fieldset>
      </div>
      <p v-if="thresholdMsg" class="faint hint">{{ thresholdMsg }}</p>
    </div>


    <button v-if="isAdmin" class="btn" type="button" @click="router.replace({ query: { section: 'connectors' } })">
      <PhPlugsConnected :size="16" /> {{ $t('Gérer les connexions') }}
    </button>
    <p v-if="message" class="muted">{{ message }}</p>
    <p v-if="error" class="error-text">{{ error }}</p>
  </section>
</template>

<style scoped>
.block {
  display: grid;
  gap: 10px;
}
.block h3 {
  font-size: 16px;
}
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.hint {
  font-size: 12.5px;
}
p {
  margin: 0;
}
.thresholds {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  align-items: start;
  gap: 12px;
}
.metric {
  margin: 0;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-md);
  padding: 10px 14px 14px;
  display: grid;
  gap: 10px;
  background: rgb(var(--surface-rgb) / 0.35);
}
.metric legend {
  font-weight: 650;
  font-size: 13.5px;
  padding: 0 6px;
}
.metric:disabled {
  opacity: 0.7;
}
.conn h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 0 6px;
  font-size: 14px;
}
.guests {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
}
.guests li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  background: rgb(var(--surface-rgb) / 0.4);
  font-size: 13.5px;
}
.name {
  flex: 1;
  min-width: 0;
}
.check {
  font-size: 13px;
}
.btn.danger {
  color: var(--down);
}
.sec > .btn {
  justify-self: start;
}
</style>
