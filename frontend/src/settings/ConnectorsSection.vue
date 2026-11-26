<script setup lang="ts">
import { serverText } from '@/i18n/server'
import { PhCheckCircle, PhPencilSimple, PhTrash, PhWarningCircle } from '@phosphor-icons/vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '@/api/client'
import type { ConnectorInstance } from '@/api/types'
import { since } from '@/design-system/time'
import { CONNECTOR_TYPES, type ConnectorType, typeInfo } from '@/spaces/cockpit/connectorTypes'
import DemoBadge from '@/spaces/cockpit/DemoBadge.vue'
import { t, tk } from '@/i18n'

const items = ref<ConnectorInstance[]>([])
const editing = ref<string | 'new' | null>(null)
const picking = ref(false)
const busy = ref(false)
const error = ref('')
const testResult = ref<Record<string, { ok: boolean; message: string }>>({})
const confirmId = ref<string | null>(null)

const DEFAULT_PORT: Record<ConnectorType, number> = { proxmox: 8006, unifi: 443, synology: 161, docker: 2376 }
const blank = (type: ConnectorType) => ({
  type,
  name: CONNECTOR_TYPES[type].label,
  mode: 'live' as 'live' | 'demo',
  host: '',
  port: DEFAULT_PORT[type],
  tls_fingerprint: '',
  // Proxmox
  token_id: 'mypds@pve!monitor',
  token_secret: '',
  // UniFi
  site: '',
  api_key: '',
  // Synology
  snmp_user: 'mypds',
  snmp_auth: 'SHA',
  snmp_priv: 'AES',
  snmp_auth_key: '',
  snmp_priv_key: '',
  dsm_enabled: false,
  dsm_port: 5001,
  dsm_user: '',
  dsm_password: '',
  url: '',
  // Docker
  ca_pem: '',
  cert_pem: '',
  key_pem: '',
})
const form = reactive(blank('proxmox'))
const info = computed(() => CONNECTOR_TYPES[form.type])
const isNew = computed(() => editing.value === 'new')

async function load() {
  items.value = await api<ConnectorInstance[]>('/api/v1/connectors')
}
onMounted(load)

function startNew(type: ConnectorType) {
  Object.assign(form, blank(type))
  picking.value = false
  editing.value = 'new'
  error.value = ''
}
function startEdit(c: ConnectorInstance) {
  const cfg = c.config as Record<string, unknown>
  const type = c.type as ConnectorType
  Object.assign(form, blank(type), {
    name: c.name,
    mode: (cfg.mode as 'live' | 'demo') ?? 'live',
    host: (cfg.host as string) ?? '',
    port: (cfg.port as number) ?? (cfg.snmp_port as number) ?? DEFAULT_PORT[type],
    tls_fingerprint: (cfg.tls_fingerprint as string) ?? '',
    token_id: (cfg.token_id as string) ?? '',
    site: (cfg.site as string) ?? '',
    snmp_user: (cfg.snmp_user as string) ?? '',
    snmp_auth: (cfg.snmp_auth as string) ?? 'SHA',
    snmp_priv: (cfg.snmp_priv as string) ?? 'AES',
    dsm_enabled: !!cfg.dsm_enabled,
    dsm_port: (cfg.dsm_port as number) ?? 5001,
    dsm_user: (cfg.dsm_user as string) ?? '',
    url: (cfg.url as string) ?? '',
  })
  editing.value = c.id
  error.value = ''
}

const trim = (v: string) => v.trim()
const opt = (k: string, v: string) => (v.trim() ? { [k]: v.trim() } : {})

/** Configuration (non secrète) et secrets selon le type. Un secret vide = inchangé. */
function payload(): { config: Record<string, unknown>; secrets: Record<string, string> } {
  if (form.mode === 'demo') return { config: { mode: 'demo' }, secrets: {} }
  const base = { mode: 'live', host: trim(form.host) }
  const secret = (k: string, v: string) => (v.trim() ? { [k]: k.endsWith('_pem') ? v.trim() + '\n' : v.trim() } : {})
  switch (form.type) {
    case 'proxmox':
      return { config: { ...base, port: form.port, token_id: trim(form.token_id), ...opt('tls_fingerprint', form.tls_fingerprint) }, secrets: secret('token_secret', form.token_secret) }
    case 'unifi':
      return { config: { ...base, port: form.port, ...opt('site', form.site), ...opt('tls_fingerprint', form.tls_fingerprint) }, secrets: secret('api_key', form.api_key) }
    case 'synology':
      return {
        config: {
          ...base,
          snmp_port: form.port,
          snmp_user: trim(form.snmp_user),
          snmp_auth: form.snmp_auth,
          snmp_priv: form.snmp_priv,
          dsm_enabled: form.dsm_enabled,
          dsm_port: form.dsm_port,
          ...opt('dsm_user', form.dsm_user),
          ...opt('tls_fingerprint', form.tls_fingerprint),
          ...opt('url', form.url),
        },
        secrets: { ...secret('snmp_auth_key', form.snmp_auth_key), ...secret('snmp_priv_key', form.snmp_priv_key), ...secret('dsm_password', form.dsm_password) },
      }
    case 'docker':
      return { config: { ...base, port: form.port }, secrets: { ...secret('ca_pem', form.ca_pem), ...secret('cert_pem', form.cert_pem), ...secret('key_pem', form.key_pem) } }
  }
}

async function save() {
  busy.value = true
  error.value = ''
  const { config, secrets } = payload()
  try {
    if (isNew.value) await api('/api/v1/connectors', { method: 'POST', json: { type: form.type, name: form.name, config, secrets } })
    else await api(`/api/v1/connectors/${editing.value}`, { method: 'PATCH', json: { name: form.name, config, secrets } })
    editing.value = null
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
    // Les secrets ne restent jamais dans le formulaire
    Object.assign(form, { token_secret: '', api_key: '', snmp_auth_key: '', snmp_priv_key: '', dsm_password: '', ca_pem: '', cert_pem: '', key_pem: '' })
  }
}

async function test(c: ConnectorInstance) {
  testResult.value[c.id] = { ok: false, message: t('Test en cours…') }
  testResult.value[c.id] = await api<{ ok: boolean; message: string }>(`/api/v1/connectors/${c.id}/test`, { method: 'POST' })
  await load()
}
async function toggle(c: ConnectorInstance) {
  await api(`/api/v1/connectors/${c.id}`, { method: 'PATCH', json: { enabled: !c.enabled } })
  await load()
}
async function remove(c: ConnectorInstance) {
  if (confirmId.value !== c.id) {
    confirmId.value = c.id
    return
  }
  await api(`/api/v1/connectors/${c.id}`, { method: 'DELETE' })
  confirmId.value = null
  await load()
}
const STATUS = { ok: tk('Connecté'), degraded: tk('Instable'), error: tk('En erreur'), unknown: tk('Jamais contacté') } as Record<string, string>
const DEMO_DESC: Record<ConnectorType, string> = {
  proxmox: tk('Données fictives (2 nœuds, 8 invités), signalées par un badge « Démo » partout. Aucun équipement n\'est interrogé.'),
  unifi: tk('Données fictives (passerelle, switch, 2 bornes Wi-Fi), signalées par un badge « Démo » partout.'),
  synology: tk('Données fictives (NAS 4 disques, 2 stockages, 2 sauvegardes), signalées par un badge « Démo » partout.'),
  docker: tk('Données fictives (6 conteneurs), signalées par un badge « Démo » partout.'),
}
const where = (c: ConnectorInstance) => {
  const cfg = c.config as Record<string, unknown>
  return cfg.host ? `${cfg.host}${cfg.port ? `:${cfg.port}` : ''}` : ''
}
const logo = (type: string) => ({ maskImage: `url(/icons/simple/${typeInfo(type).icon}.svg)`, WebkitMaskImage: `url(/icons/simple/${typeInfo(type).icon}.svg)` })
</script>

<template>
  <section class="sec">
    <h2>{{ $t('Connexions') }}</h2>
    <p class="muted">
      {{ $t('Les équipements supervisés par le Cockpit. Lecture seule pour l\'instant : aucune action n\'est envoyée aux équipements. Les secrets sont chiffrés et ne sont jamais réaffichés.') }}
    </p>

    <ul class="list">
      <li v-for="c in items" :key="c.id">
        <span class="ic" :style="{ background: typeInfo(c.type).color }"><i class="logo" :style="logo(c.type)" /></span>
        <div class="info">
          <strong>{{ c.name }} <DemoBadge v-if="c.demo" /></strong>
          <span class="faint">
            {{ typeInfo(c.type).label }}<template v-if="!c.demo && where(c)"> · {{ where(c) }}</template> ·
            <span :class="{ okt: c.status === 'ok', bad: c.status === 'error' || c.status === 'degraded' }">{{ STATUS[c.status] ? $t(STATUS[c.status]!) : c.status }}</span>
            <template v-if="c.last_ok_at"> · {{ $t('données {when}', { when: since(c.last_ok_at) }) }}</template>
          </span>
          <span v-if="c.last_error" class="error-text"><PhWarningCircle :size="13" /> {{ serverText(c.last_error) }}</span>
          <span v-if="testResult[c.id] && testResult[c.id]!.message !== c.last_error" :class="testResult[c.id]!.ok ? 'okt' : 'error-text'">
            <PhCheckCircle v-if="testResult[c.id]!.ok" :size="13" weight="fill" /> {{ serverText(testResult[c.id]!.message) }}
          </span>
        </div>
        <label class="check" :title="c.enabled ? $t('Désactiver') : $t('Activer')"><input type="checkbox" :checked="c.enabled" :aria-label="$t('Activer {name}', { name: c.name })" @change="toggle(c)" /></label>
        <button class="btn small" type="button" @click="test(c)">{{ $t('Tester') }}</button>
        <button class="icon-btn" type="button" :aria-label="$t('Modifier {name}', { name: c.name })" @click="startEdit(c)"><PhPencilSimple :size="16" /></button>
        <button class="icon-btn" :class="{ danger: confirmId === c.id }" type="button" :aria-label="confirmId === c.id ? $t('Confirmer la suppression') : $t('Supprimer {name}', { name: c.name })" @click="remove(c)" @blur="confirmId = null"><PhTrash :size="16" /></button>
      </li>
      <li v-if="!items.length" class="faint empty">{{ $t('Aucune connexion.') }}</li>
    </ul>

    <template v-if="!editing">
      <button v-if="!picking" class="btn primary add" type="button" @click="picking = true">{{ $t('Ajouter une connexion') }}</button>
      <div v-else class="picker">
        <p class="pick-title">{{ $t('Quel équipement ?') }}</p>
        <div class="types">
          <button v-for="(ti, key) in CONNECTOR_TYPES" :key="key" type="button" class="type" @click="startNew(key)">
            <span class="ic" :style="{ background: ti.color }"><i class="logo" :style="logo(key)" /></span>
            <span><strong>{{ ti.label }}<em v-if="ti.experimental" class="exp">{{ $t('expérimental') }}</em></strong><span class="faint">{{ $t(ti.desc) }}</span></span>
          </button>
        </div>
        <button class="btn small" type="button" @click="picking = false">{{ $t('Annuler') }}</button>
      </div>
    </template>

    <form v-else class="form" @submit.prevent="save">
      <h3>
        <span class="ic sm" :style="{ background: info.color }"><i class="logo" :style="logo(form.type)" /></span>
        {{ isNew ? $t('Nouvelle connexion {type}', { type: info.label }) : $t('Modifier la connexion') }}
      </h3>
      <label class="field"><span>{{ $t('Nom') }}</span><input v-model="form.name" class="input" required maxlength="80" /></label>
      <div class="field">
        <span>{{ $t('Source des données') }}</span>
        <div class="seg">
          <button type="button" :aria-pressed="form.mode === 'live'" @click="form.mode = 'live'">{{ $t('Mon équipement') }}</button>
          <button type="button" :aria-pressed="form.mode === 'demo'" @click="form.mode = 'demo'">{{ $t('Démonstration') }}</button>
        </div>
        <p v-if="form.mode === 'demo'" class="faint hint">{{ $t(DEMO_DESC[form.type]) }}</p>
        <p v-else-if="info.experimental" class="hint exp-note">{{ $t('Connecteur expérimental : il n\'a pas encore été validé sur du vrai matériel. Signalez ce qui ne fonctionne pas sur la page du projet.') }}</p>
      </div>

      <template v-if="form.mode === 'live'">
        <div class="grid2">
          <label class="field"><span>{{ $t('Adresse (IP ou nom)') }}</span><input v-model="form.host" class="input" required :placeholder="form.type === 'unifi' ? '192.168.1.1' : '192.168.1.10'" autocapitalize="none" spellcheck="false" /></label>
          <label class="field"><span>{{ form.type === 'synology' ? $t('Port SNMP') : $t('Port') }}</span><input v-model.number="form.port" class="input" type="number" min="1" max="65535" /></label>
        </div>

        <!-- Proxmox -->
        <template v-if="form.type === 'proxmox'">
          <label class="field"><span>{{ $t('Identifiant du jeton API') }}</span><input v-model="form.token_id" class="input" required :placeholder="$t('mypds@pve!monitor')" autocapitalize="none" spellcheck="false" /></label>
          <label class="field">
            <span>{{ $t('Secret du jeton') }}</span>
            <input v-model="form.token_secret" class="input" type="password" autocomplete="new-password" :required="isNew" :placeholder="isNew ? 'xxxxxxxx-xxxx-…' : $t('Inchangé')" />
          </label>
        </template>

        <!-- UniFi -->
        <template v-if="form.type === 'unifi'">
          <label class="field">
            <span>{{ $t('Clé API (intégration)') }}</span>
            <input v-model="form.api_key" class="input" type="password" autocomplete="new-password" :required="isNew" :placeholder="isNew ? '' : $t('Inchangé')" />
          </label>
          <label class="field"><span>{{ $t('Site (facultatif)') }}</span><input v-model="form.site" class="input" :placeholder="$t('Vide = premier site')" /></label>
        </template>

        <!-- Synology -->
        <template v-if="form.type === 'synology'">
          <label class="field"><span>{{ $t('Utilisateur SNMP v3') }}</span><input v-model="form.snmp_user" class="input" required autocapitalize="none" spellcheck="false" /></label>
          <div class="grid2 even">
            <label class="field">
              <span>{{ $t('Authentification') }}</span>
              <select v-model="form.snmp_auth" class="input"><option value="SHA">SHA</option><option value="SHA256">SHA-256</option><option value="MD5">MD5</option></select>
            </label>
            <label class="field">
              <span>{{ $t('Chiffrement') }}</span>
              <select v-model="form.snmp_priv" class="input"><option value="AES">AES</option><option value="DES">DES</option></select>
            </label>
          </div>
          <div class="grid2 even">
            <label class="field"><span>{{ $t('Mot de passe d\'authentification') }}</span><input v-model="form.snmp_auth_key" class="input" type="password" autocomplete="new-password" minlength="8" :required="isNew" :placeholder="isNew ? '' : $t('Inchangé')" /></label>
            <label class="field"><span>{{ $t('Mot de passe de chiffrement') }}</span><input v-model="form.snmp_priv_key" class="input" type="password" autocomplete="new-password" minlength="8" :required="isNew" :placeholder="isNew ? '' : $t('Inchangé')" /></label>
          </div>
          <label class="check"><input v-model="form.dsm_enabled" type="checkbox" /> {{ $t('Lire aussi l\'état des sauvegardes Hyper Backup (API DSM, compte dédié)') }}</label>
          <template v-if="form.dsm_enabled">
            <div class="grid2">
              <label class="field"><span>{{ $t('Compte DSM') }}</span><input v-model="form.dsm_user" class="input" required autocapitalize="none" spellcheck="false" /></label>
              <label class="field"><span>{{ $t('Port HTTPS de DSM') }}</span><input v-model.number="form.dsm_port" class="input" type="number" min="1" max="65535" /></label>
            </div>
            <label class="field"><span>{{ $t('Mot de passe DSM') }}</span><input v-model="form.dsm_password" class="input" type="password" autocomplete="new-password" :placeholder="isNew ? '' : $t('Inchangé')" /></label>
            <p class="faint hint">{{ $t('Le compte ne doit pas avoir la double authentification. Si votre version de DSM n\'expose pas Hyper Backup, l\'information est indiquée « non disponible ».') }}</p>
          </template>
          <label class="field"><span>{{ $t('Lien vers DSM (clic sur la tuile, facultatif)') }}</span><input v-model="form.url" class="input" type="url" placeholder="https://nas.home.lan:5001" /></label>
        </template>

        <!-- Docker -->
        <template v-if="form.type === 'docker'">
          <p class="warn">
            <PhWarningCircle :size="16" weight="fill" />
            {{ $t('Le certificat client Docker donne un accès complet (root) à l\'hôte. MyPDS ne fait que lire, mais utilisez un certificat dédié et n\'ouvrez le port 2376 qu\'au serveur MyPDS.') }}
          </p>
          <label class="field"><span>{{ $t('Autorité (ca.pem)') }}</span><textarea v-model="form.ca_pem" class="input pem" rows="3" :required="isNew" :placeholder="isNew ? '-----BEGIN CERTIFICATE-----' : $t('Inchangé')" spellcheck="false" /></label>
          <label class="field"><span>{{ $t('Certificat client (cert.pem)') }}</span><textarea v-model="form.cert_pem" class="input pem" rows="3" :required="isNew" :placeholder="isNew ? '-----BEGIN CERTIFICATE-----' : $t('Inchangé')" spellcheck="false" /></label>
          <label class="field"><span>{{ $t('Clé client (key.pem)') }}</span><textarea v-model="form.key_pem" class="input pem" rows="3" :required="isNew" :placeholder="isNew ? '-----BEGIN PRIVATE KEY-----' : $t('Inchangé')" spellcheck="false" /></label>
        </template>

        <label v-if="form.type !== 'docker'" class="field">
          <span>{{ $t('Empreinte SHA-256 du certificat (si auto-signé)') }}</span>
          <input v-model="form.tls_fingerprint" class="input" :placeholder="$t('AB:CD:EF:…')" autocapitalize="none" spellcheck="false" />
        </label>

        <details class="howto">
          <summary>{{ $t('Créer l\'accès en lecture seule') }}</summary>
          <ol v-if="form.type === 'proxmox'">
            <li>{{ $t('Sur un nœud, en shell root :') }} <code>{{ $t('pveum user add mypds@pve --comment "My Personal Digital Space"') }}</code></li>
            <li>{{ $t('Droits de lecture seule :') }} <code>{{ $t('pveum acl modify / --users mypds@pve --roles PVEAuditor') }}</code></li>
            <li>{{ $t('Jeton :') }} <code>{{ $t('pveum user token add mypds@pve monitor --privsep 0') }}</code> {{ $t('— copiez la valeur affichée (une seule fois).') }}</li>
            <li>{{ $t('Empreinte du certificat :') }} <code>{{ $t('pvenode cert info --output-format json | grep -i fingerprint') }}</code> {{ $t('(ou Nœud → Système → Certificats).') }}</li>
          </ol>
          <ol v-else-if="form.type === 'unifi'">
            <li>{{ $t('Dans UniFi Network : Paramètres → Control Plane → Intégrations → Créer une clé API.') }}</li>
            <li>{{ $t('Copiez la clé (affichée une seule fois) et collez-la ci-dessus.') }}</li>
            <li>{{ $t('Empreinte du certificat de la console, depuis un Terminal :') }} <code>openssl s_client -connect {{ form.host || '192.168.0.1' }}:{{ form.port }} &lt;/dev/null 2&gt;/dev/null | openssl x509 -noout -fingerprint -sha256</code> {{ $t('(ou dans le navigateur : avertissement de sécurité → certificat → empreinte SHA-256).') }}</li>
          </ol>
          <ol v-else-if="form.type === 'synology'">
            <li>{{ $t('DSM : Panneau de configuration → Terminal & SNMP → SNMP : activer le service SNMP, cocher SNMPv3 seulement.') }}</li>
            <li>{{ $t('Créer l\'utilisateur SNMP (ex. mypds) avec authentification SHA et chiffrement AES, deux mots de passe d\'au moins 8 caractères.') }}</li>
            <li>{{ $t('Autoriser le port 161/UDP depuis le serveur MyPDS dans le pare-feu du NAS.') }}</li>
            <li>{{ $t('Facultatif (Hyper Backup) : créer un compte DSM dédié, sans double authentification.') }}</li>
          </ol>
          <ol v-else>
            <li>{{ $t('Sur l\'hôte Docker, créer une autorité (CA), un certificat serveur contenant son adresse, et un certificat client dédié à MyPDS (guide officiel « Protect the Docker daemon socket »).') }}</li>
            <li>{{ $t('Lancer dockerd avec --tlsverify et les certificats serveur, sur le port 2376.') }}</li>
            <li>{{ $t('Coller ici ca.pem, cert.pem et key.pem du client.') }}</li>
          </ol>
          <p class="faint">{{ form.type === 'docker' ? $t('MyPDS n\'envoie que des lectures (liste, état, statistiques) : aucun démarrage, arrêt ou modification.') : form.type === 'proxmox' ? $t('Le jeton n\'a que le rôle PVEAuditor : il ne peut ni démarrer, ni arrêter, ni modifier quoi que ce soit.') : $t('MyPDS n\'envoie que des lectures : aucune modification de l\'équipement.') }}</p>
        </details>
      </template>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div class="actions">
        <button class="btn primary" type="submit" :disabled="busy">{{ busy ? $t('Connexion…') : $t('Enregistrer') }}</button>
        <button class="btn" type="button" @click="editing = null">{{ $t('Annuler') }}</button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: rgb(var(--surface-rgb) / 0.5);
  flex-wrap: wrap;
}
.ic {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  color: #fff;
  flex: none;
}
.ic.sm {
  width: 28px;
  height: 28px;
  border-radius: 8px;
}
.logo {
  width: 58%;
  height: 58%;
  background: #fff;
  mask-size: contain;
  mask-repeat: no-repeat;
  mask-position: center;
  -webkit-mask-size: contain;
  -webkit-mask-repeat: no-repeat;
  -webkit-mask-position: center;
}
.info {
  flex: 1;
  min-width: 200px;
  display: grid;
  gap: 2px;
  font-size: 13px;
}
.info strong {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14.5px;
}
.okt {
  color: var(--ok);
  font-weight: 600;
}
.bad {
  color: var(--down);
  font-weight: 600;
}
.icon-btn.danger {
  background: var(--down);
  color: #fff;
}
.add {
  justify-self: start;
}
.picker {
  display: grid;
  gap: 10px;
  justify-items: start;
}
.exp {
  margin-left: 8px;
  padding: 1px 7px;
  border-radius: 999px;
  background: rgb(255 159 10 / 0.16);
  color: var(--warn);
  font-size: 11px;
  font-style: normal;
  font-weight: 650;
  vertical-align: 1px;
}
.exp-note {
  color: var(--warn);
}
.pick-title {
  margin: 0;
  font-weight: 600;
}
.types {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 8px;
}
.type {
  display: flex;
  gap: 12px;
  align-items: center;
  text-align: left;
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--hairline);
  background: rgb(var(--surface-rgb) / 0.55);
  transition: background var(--dur-fast), transform var(--dur-fast);
}
.type:hover {
  background: rgb(var(--surface-rgb) / 0.9);
  transform: translateY(-1px);
}
.type > span:last-child {
  display: grid;
  gap: 2px;
  font-size: 13px;
}
.form {
  display: grid;
  gap: 14px;
  padding-top: 8px;
}
.form h3 {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 140px;
  gap: 12px;
}
.grid2.even {
  grid-template-columns: 1fr 1fr;
}
.pem {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  min-height: 64px;
  resize: vertical;
}
.warn {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin: 0;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--warn, #ff9500) 16%, transparent);
  font-size: 13px;
}
.hint {
  margin: 0;
  font-size: 12.5px;
}
.howto {
  font-size: 13.5px;
  border-radius: var(--radius-md);
  background: rgb(var(--surface-rgb) / 0.4);
  padding: 10px 14px;
}
.howto summary {
  cursor: pointer;
  font-weight: 600;
}
.howto ol {
  padding-left: 20px;
  display: grid;
  gap: 6px;
}
code {
  font-size: 12px;
  background: rgb(var(--surface-rgb) / 0.7);
  padding: 1px 6px;
  border-radius: 6px;
  word-break: break-all;
}
.actions {
  display: flex;
  gap: 8px;
}
.empty {
  justify-content: center;
}
@media (max-width: 560px) {
  .grid2,
  .grid2.even {
    grid-template-columns: 1fr;
  }
}
</style>
