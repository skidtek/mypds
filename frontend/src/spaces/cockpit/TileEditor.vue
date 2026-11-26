<script setup lang="ts">
import { PhBell, PhChartDonut, PhClockCounterClockwise, PhCube, PhDatabase, PhHardDrives, PhLink, PhNetwork, PhPackage, PhStack, PhWifiHigh } from '@phosphor-icons/vue'
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { CockpitTile, DockerData, IconRef, TileType, UnifiData } from '@/api/types'
import GlassDialog from '@/design-system/components/GlassDialog.vue'
import { useCockpit } from '@/stores/cockpit'
import { useSession } from '@/stores/session'
import IconPicker from './IconPicker.vue'
import TileIcon from './TileIcon.vue'
import { t as tr, tk } from '@/i18n'

const props = defineProps<{ tile?: CockpitTile; groupId: string; rowId?: string }>()
const emit = defineEmits<{ close: [] }>()
const store = useCockpit()
const session = useSession()
const router = useRouter()

const TYPES: { id: TileType; name: string; desc: string; icon: unknown; width: number }[] = [
  { id: 'proxmox.summary', name: tk('Résumé Proxmox'), desc: tk('État du cluster, quorum, invités, CPU, mémoire, stockage.'), icon: PhChartDonut, width: 12 },
  { id: 'proxmox.node', name: tk('Nœud Proxmox'), desc: tk("Charge d'un serveur PVE avec l'historique de la dernière heure."), icon: PhHardDrives, width: 4 },
  { id: 'proxmox.guest', name: tk('Serveur (VM / LXC)'), desc: tk("Nom, logo, pastille d'état ; un clic ouvre le service."), icon: PhCube, width: 3 },
  { id: 'unifi.summary', name: tk('Résumé UniFi'), desc: tk('Internet (débit en direct), équipements, clients, charge de la passerelle.'), icon: PhNetwork, width: 12 },
  { id: 'unifi.device', name: tk('Équipement UniFi'), desc: tk('Passerelle, switch ou borne Wi-Fi : état, charge, mise à jour.'), icon: PhWifiHigh, width: 3 },
  { id: 'synology.summary', name: tk('Résumé Synology'), desc: tk('État du NAS, volumes, disques, températures, sauvegardes.'), icon: PhDatabase, width: 12 },
  { id: 'docker.summary', name: tk('Résumé Docker'), desc: tk('Conteneurs en marche, problèmes, plus actifs, hôte.'), icon: PhStack, width: 12 },
  { id: 'docker.container', name: tk('Conteneur Docker'), desc: tk("Nom, logo, pastille d'état ; un clic ouvre le service."), icon: PhPackage, width: 3 },
  { id: 'link', name: tk('Lien'), desc: tk("Raccourci vers un service (GRR, Printr…), sans supervision."), icon: PhLink, width: 3 },
  { id: 'alerts', name: tk('Alertes & notifications'), desc: tk('Problèmes détectés en direct, sauvegardes réussies, alertes résolues.'), icon: PhBell, width: 6 },
  { id: 'activity', name: tk('Dernières activités'), desc: tk('Dernières tâches Proxmox : sauvegardes, démarrages, migrations…'), icon: PhClockCounterClockwise, width: 6 },
]

const type = ref<TileType | null>(props.tile?.type ?? null)
const form = reactive({
  connector_id: props.tile?.config.connector_id ?? '',
  node: props.tile?.config.node ?? '',
  guest: props.tile?.config.guest ?? '',
  device: props.tile?.config.device ?? '',
  container: props.tile?.config.container ?? '',
  label: props.tile?.config.label ?? '',
  url: props.tile?.config.url ?? '',
  icon: (props.tile?.config.icon ?? null) as IconRef | null,
  width: props.tile?.width.desktop ?? 3,
  on_demand: false,
})
const picking = ref(false)
const error = ref('')

const CONNECTOR_LABELS: Record<string, string> = { proxmox: 'Proxmox', unifi: 'UniFi', synology: 'Synology', docker: 'Docker' }
/** Type de connexion attendu par la tuile (« unifi.device » → « unifi »). */
const ctype = computed(() => {
  const p = type.value?.split('.')[0] ?? ''
  return p in CONNECTOR_LABELS ? p : null
})
const conns = computed(() => store.snapshots.filter((s) => s.type === ctype.value))
const snap = computed(() => store.snapshot(form.connector_id))
const needsConnector = computed(() => !!ctype.value)
const selectedGuest = computed(() => snap.value?.data?.guest_list?.find((g) => g.id === form.guest))
const devices = computed(() => (snap.value?.data as unknown as UnifiData | null)?.devices ?? [])
const containers = computed(() => (snap.value?.data as unknown as DockerData | null)?.containers ?? [])
const selectedContainer = computed(() => containers.value.find((c) => c.name === form.container))
form.on_demand = props.tile?.type === 'docker.container'
  ? !!selectedContainer.value?.on_demand
  : !!store.guest(form.connector_id, form.guest)?.on_demand

function choose(t: (typeof TYPES)[number]) {
  type.value = t.id
  if (!props.tile) form.width = t.width
  if (!conns.value.some((c) => c.id === form.connector_id)) form.connector_id = conns.value[0]?.id ?? ''
}

function save() {
  error.value = ''
  const t = type.value
  if (!t) return
  const config: CockpitTile['config'] = {}
  if (needsConnector.value) {
    if (!form.connector_id) return void (error.value = tr('Choisissez une connexion {type}.', { type: CONNECTOR_LABELS[ctype.value!] }))
    config.connector_id = form.connector_id
  }
  if (t === 'proxmox.node') {
    if (!form.node) return void (error.value = tr('Choisissez un nœud.'))
    config.node = form.node
  }
  if (t === 'proxmox.guest') {
    if (!form.guest) return void (error.value = tr('Choisissez une VM ou un conteneur.'))
    config.guest = form.guest
  }
  if (t === 'unifi.device') {
    if (!form.device) return void (error.value = tr('Choisissez un équipement.'))
    config.device = form.device
    if (form.label.trim()) config.label = form.label.trim()
  }
  if (t === 'docker.container') {
    if (!form.container) return void (error.value = tr('Choisissez un conteneur.'))
    config.container = form.container
  }
  if (t === 'proxmox.guest' || t === 'docker.container' || t === 'link') {
    const url = form.url.trim()
    if (url && !/^https?:\/\//i.test(url)) return void (error.value = "L'adresse doit commencer par http:// ou https://")
    if (t === 'link' && !url) return void (error.value = "L'adresse du service est requise.")
    if (t === 'link' && !form.label.trim()) return void (error.value = tr('Le nom est requis.'))
    if (url) config.url = url
    if (form.label.trim()) config.label = form.label.trim()
    if (form.icon) config.icon = form.icon
  }
  const patch = { type: t, width: { desktop: form.width }, config }
  if (props.tile) store.updateTile(props.tile.id, patch)
  else store.addTile(props.groupId, props.rowId!, patch)
  if (t === 'proxmox.guest' && session.me?.role === 'admin' && form.on_demand !== !!selectedGuest.value?.on_demand) {
    void store.setOnDemand(form.connector_id, form.guest, form.on_demand)
  }
  if (t === 'docker.container' && session.me?.role === 'admin' && form.on_demand !== !!selectedContainer.value?.on_demand) {
    void store.setOnDemand(form.connector_id, form.container, form.on_demand)
  }
  emit('close')
}

function goConnectors() {
  emit('close')
  void router.push({ name: 'settings', query: { section: 'connectors' } })
}
</script>

<template>
  <GlassDialog :title="tile ? $t('Configurer la tuile') : $t('Ajouter une tuile')" @close="emit('close')">
    <ul v-if="!type" class="types">
      <li v-for="t in TYPES" :key="t.id">
        <button type="button" @click="choose(t)">
          <span class="ic"><component :is="t.icon" :size="22" /></span>
          <span><strong>{{ $t(t.name) }}</strong><span class="muted">{{ $t(t.desc) }}</span></span>
        </button>
      </li>
    </ul>
    <template v-else>
      <template v-if="needsConnector">
        <p v-if="!conns.length" class="muted">
          {{ $t('Aucune connexion {type}.', { type: CONNECTOR_LABELS[ctype!] }) }}
          <button v-if="session.me?.role === 'admin'" class="link" type="button" @click="goConnectors">{{ $t('Ajouter une connexion') }}</button>
          <span v-else>{{ $t('Demandez à un administrateur d\'en ajouter une.') }}</span>
        </p>
        <label v-else class="field">
          <span>{{ $t('Connexion {type}', { type: CONNECTOR_LABELS[ctype!] }) }}</span>
          <select v-model="form.connector_id" class="input">
            <option v-for="s in conns" :key="s.id" :value="s.id">{{ s.name }}{{ s.demo ? ` (${$t('démo')})` : '' }}</option>
          </select>
        </label>
      </template>

      <label v-if="type === 'proxmox.node'" class="field">
        <span>{{ $t('Nœud') }}</span>
        <select v-model="form.node" class="input">
          <option value="" disabled>{{ $t('Choisir…') }}</option>
          <option v-for="n in snap?.data?.nodes ?? []" :key="n.name" :value="n.name">{{ n.name }}{{ n.online ? '' : ` (${$t('hors ligne')})` }}</option>
        </select>
      </label>

      <label v-if="type === 'proxmox.guest'" class="field">
        <span>{{ $t('VM ou conteneur') }}</span>
        <select v-model="form.guest" class="input">
          <option value="" disabled>{{ $t('Choisir…') }}</option>
          <option v-for="g in snap?.data?.guest_list ?? []" :key="g.id" :value="g.id">
            {{ g.name }} — {{ g.type === 'qemu' ? 'VM' : 'LXC' }} {{ g.vmid }} · {{ g.node }} · {{ g.status === 'running' ? $t('en marche') : $t('arrêté') }}
          </option>
        </select>
      </label>

      <label v-if="type === 'unifi.device'" class="field">
        <span>{{ $t('Équipement') }}</span>
        <select v-model="form.device" class="input">
          <option value="" disabled>{{ $t('Choisir…') }}</option>
          <option v-for="d in devices" :key="d.id" :value="d.id">{{ d.name }} — {{ d.model }}{{ d.online ? '' : ` (${$t('hors ligne')})` }}</option>
        </select>
      </label>
      <label v-if="type === 'unifi.device'" class="field">
        <span>{{ $t('Nom affiché (facultatif)') }}</span>
        <input v-model="form.label" class="input" maxlength="60" />
      </label>

      <label v-if="type === 'docker.container'" class="field">
        <span>{{ $t('Conteneur') }}</span>
        <select v-model="form.container" class="input">
          <option value="" disabled>{{ $t('Choisir…') }}</option>
          <option v-for="c in containers" :key="c.id" :value="c.name">{{ c.name }} — {{ c.image }} · {{ c.state === 'running' ? $t('en marche') : $t('arrêté') }}</option>
        </select>
      </label>
      <label v-if="type === 'docker.container' && session.me?.role === 'admin' && form.container" class="check">
        <input v-model="form.on_demand" type="checkbox" />
        {{ $t('Démarré à la demande : pas d\'alerte quand il est arrêté') }}
      </label>

      <label v-if="type === 'proxmox.guest' && session.me?.role === 'admin' && form.guest" class="check">
        <input v-model="form.on_demand" type="checkbox" />
        {{ $t('Démarrée à la demande : pas d\'alerte quand elle est arrêtée') }}
      </label>

      <template v-if="type === 'proxmox.guest' || type === 'docker.container' || type === 'link'">
        <label class="field">
          <span>{{ type === 'link' ? $t('Nom affiché') : $t('Nom affiché (facultatif)') }}</span>
          <input v-model="form.label" class="input" maxlength="60" :placeholder="selectedGuest?.name ?? selectedContainer?.name ?? 'GRR'" />
        </label>
        <label class="field">
          <span>{{ type === 'link' ? $t('Adresse du service') : $t('Adresse du service (ouverte au clic)') }}</span>
          <input v-model="form.url" class="input" inputmode="url" :placeholder="$t('https://service.home.lan')" />
        </label>
        <div class="field">
          <span>{{ $t('Logo') }}</span>
          <div class="icon-row">
            <TileIcon :icon="form.icon" :fallback="type === 'link' ? 'link' : form.guest.startsWith('qemu') ? 'qemu' : 'lxc'" :size="44" />
            <button class="btn small" type="button" @click="picking = true">{{ $t('Choisir un logo') }}</button>
          </div>
        </div>
      </template>

      <label class="field">
        <span>{{ $t('Largeur sur ordinateur : {n}/12 colonnes', { n: form.width }) }}</span>
        <input v-model.number="form.width" type="range" min="1" max="12" />
      </label>
      <p v-if="error" class="error-text">{{ error }}</p>
    </template>
    <template v-if="type" #footer>
      <button v-if="!tile" class="btn" type="button" @click="type = null">{{ $t('Retour') }}</button>
      <button class="btn primary" type="button" @click="save">{{ tile ? 'Enregistrer' : 'Ajouter' }}</button>
    </template>
  </GlassDialog>
  <IconPicker
    v-if="picking"
    :initial-query="form.label || selectedGuest?.name || selectedContainer?.name || ''"
    @close="picking = false"
    @pick="(i) => { form.icon = i; picking = false }"
  />
</template>

<style scoped>
.types {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.types button {
  width: 100%;
  display: flex;
  gap: 14px;
  align-items: center;
  text-align: left;
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--hairline);
  background: rgb(var(--surface-rgb) / 0.55);
}
.types button:hover {
  background: rgb(var(--surface-rgb) / 0.9);
}
.types button > span:last-child {
  display: grid;
  gap: 2px;
  font-size: 13.5px;
}
.ic {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: #fff;
  background: linear-gradient(135deg, #5ac8fa, #7d6cf2);
  flex: none;
}
.icon-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.link {
  border: none;
  background: none;
  color: var(--accent);
  font-weight: 600;
  padding: 0;
}
p {
  margin: 0;
}
</style>
