<script setup lang="ts">
import { serverText } from '@/i18n/server'
import { PhArrowClockwise, PhKey, PhLockSimple, PhTrash, PhWarningCircle } from '@phosphor-icons/vue'
import { onMounted, ref, watch } from 'vue'
import { api } from '@/api/client'
import type { CalendarSource } from '@/api/types'
import { since } from '@/design-system/time'

const sources = ref<CalendarSource[]>([])
const name = ref('')
const url = ref('')
const color = ref('#0A84FF')
const busy = ref(false)
const error = ref('')
const confirmId = ref<string | null>(null)
const needsAuth = ref(false)
const username = ref('')
const password = ref('')
// Édition des identifiants d'un calendrier existant
const editing = ref<string | null>(null)
const editUser = ref('')
const editPassword = ref('')
const editError = ref('')
const editBusy = ref(false)

// « https://identifiant@serveur/… » : l'identifiant passe dans son champ, hors de l'adresse
watch(url, (v) => {
  const m = /^(https?|webcal):\/\/([^/@\s]+)@/i.exec(v.trim())
  if (m) {
    const [user] = decodeURIComponent(m[2]!).split(':')
    needsAuth.value = true
    if (!username.value) username.value = user ?? ''
    url.value = v.trim().replace(`${m[2]}@`, '')
  }
})

async function load() {
  sources.value = await api<CalendarSource[]>('/api/v1/calendar/sources')
}
onMounted(load)

async function add() {
  busy.value = true
  error.value = ''
  try {
    const auth = needsAuth.value && username.value ? { username: username.value, password: password.value } : {}
    await api('/api/v1/calendar/sources', { method: 'POST', json: { name: name.value, url: url.value, color: color.value, ...auth } })
    name.value = url.value = username.value = password.value = ''
    needsAuth.value = false
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    if (/connexion|identifiant/i.test(error.value)) needsAuth.value = true
  } finally {
    busy.value = false
    password.value = password.value && error.value ? password.value : ''
  }
}

function startEdit(s: CalendarSource) {
  editing.value = editing.value === s.id ? null : s.id
  editUser.value = s.auth_username ?? ''
  editPassword.value = ''
  editError.value = ''
}

async function saveAuth(s: CalendarSource, clear = false) {
  editBusy.value = true
  editError.value = ''
  try {
    const body = clear ? { clear_auth: true } : { username: editUser.value, ...(editPassword.value ? { password: editPassword.value } : {}) }
    Object.assign(s, await api<CalendarSource>(`/api/v1/calendar/sources/${s.id}`, { method: 'PATCH', json: body }))
    editing.value = null
  } catch (e) {
    editError.value = e instanceof Error ? e.message : String(e)
  } finally {
    editBusy.value = false
    editPassword.value = ''
  }
}

async function patch(s: CalendarSource, body: Partial<CalendarSource>) {
  Object.assign(s, await api<CalendarSource>(`/api/v1/calendar/sources/${s.id}`, { method: 'PATCH', json: body }))
}
async function sync(s: CalendarSource) {
  Object.assign(s, await api<CalendarSource>(`/api/v1/calendar/sources/${s.id}/sync`, { method: 'POST' }))
}
async function remove(s: CalendarSource) {
  if (confirmId.value !== s.id) {
    confirmId.value = s.id
    return
  }
  await api(`/api/v1/calendar/sources/${s.id}`, { method: 'DELETE' })
  confirmId.value = null
  await load()
}
</script>

<template>
  <section class="sec">
    <h2>{{ $t('Agenda') }}</h2>
    <p class="muted">
      {{ $t('Ajoutez l\'adresse « iCal / ICS » de vos calendriers (Google, iCloud, Outlook, Nextcloud, SOGo…). Le serveur la récupère toutes les 15 minutes ; l\'adresse et l\'éventuel mot de passe sont chiffrés et ne sont jamais renvoyés au navigateur.') }}
    </p>
    <ul class="list">
      <li v-for="s in sources" :key="s.id">
        <input type="color" class="color" :value="s.color" :aria-label="$t('Couleur de {name}', { name: s.name })" @change="patch(s, { color: ($event.target as HTMLInputElement).value })" />
        <div class="info">
          <strong>{{ s.name }}</strong>
          <span class="faint">
            <template v-if="s.auth_username"><PhLockSimple :size="12" /> {{ s.auth_username }} · </template>
            {{ s.url_host }} · {{ $tn(s.event_count, '{n} événement', '{n} événements') }}
            <template v-if="s.last_success_at"> · {{ $t('synchronisé {when}', { when: since(s.last_success_at) }) }}</template>
          </span>
          <span v-if="s.last_error" class="error-text"><PhWarningCircle :size="13" /> {{ serverText(s.last_error) }}</span>
        </div>
        <label class="check" :title="s.enabled ? $t('Désactiver') : $t('Activer')">
          <input type="checkbox" :checked="s.enabled" :aria-label="$t('Activer {name}', { name: s.name })" @change="patch(s, { enabled: ($event.target as HTMLInputElement).checked })" />
        </label>
        <button class="icon-btn" :class="{ active: editing === s.id }" type="button" :aria-label="$t('Identifiants de {name}', { name: s.name })" :title="$t('Identifiant et mot de passe')" @click="startEdit(s)"><PhKey :size="17" /></button>
        <button class="icon-btn" type="button" :aria-label="$t('Synchroniser {name}', { name: s.name })" @click="sync(s)"><PhArrowClockwise :size="17" /></button>
        <button class="icon-btn" :class="{ danger: confirmId === s.id }" type="button" :aria-label="confirmId === s.id ? $t('Confirmer la suppression') : $t('Supprimer {name}', { name: s.name })" @click="remove(s)" @blur="confirmId = null">
          <PhTrash :size="17" />
        </button>
        <form v-if="editing === s.id" class="auth-edit" @submit.prevent="saveAuth(s)">
          <label class="field"><span>{{ $t('Identifiant') }}</span><input v-model="editUser" class="input" autocomplete="off" autocapitalize="none" spellcheck="false" /></label>
          <label class="field"><span>{{ $t('Mot de passe') }}</span><input v-model="editPassword" class="input" type="password" autocomplete="new-password" :placeholder="s.auth_username ? $t('Inchangé') : ''" /></label>
          <div class="auth-actions">
            <button class="btn small primary" type="submit" :disabled="editBusy || !editUser">{{ editBusy ? $t('Vérification…') : $t('Enregistrer') }}</button>
            <button v-if="s.auth_username" class="btn small" type="button" :disabled="editBusy" @click="saveAuth(s, true)">{{ $t('Retirer la connexion') }}</button>
          </div>
          <p v-if="editError" class="error-text">{{ editError }}</p>
        </form>
      </li>
      <li v-if="!sources.length" class="empty faint">{{ $t('Aucun calendrier pour l\'instant.') }}</li>
    </ul>
    <form class="add" @submit.prevent="add">
      <h3>{{ $t('Ajouter un calendrier ICS') }}</h3>
      <div class="grid2">
        <label class="field"><span>{{ $t('Nom') }}</span><input v-model="name" class="input" required maxlength="80" :placeholder="$t('Perso')" /></label>
        <label class="field"><span>{{ $t('Couleur') }}</span><input v-model="color" type="color" class="color big" /></label>
      </div>
      <label class="field"><span>{{ $t('Adresse ICS / iCal (https:// ou webcal://)') }}</span><input v-model="url" class="input" required inputmode="url" autocomplete="off" :placeholder="$t('https://…/basic.ics')" /></label>
      <label class="check"><input v-model="needsAuth" type="checkbox" /> {{ $t('Ce calendrier demande une connexion (identifiant et mot de passe)') }}</label>
      <div v-if="needsAuth" class="grid-auth">
        <label class="field"><span>{{ $t('Identifiant') }}</span><input v-model="username" class="input" required autocomplete="off" autocapitalize="none" spellcheck="false" /></label>
        <label class="field"><span>{{ $t('Mot de passe') }}</span><input v-model="password" class="input" type="password" required autocomplete="new-password" /></label>
        <p class="faint hint">{{ $t('Envoyé uniquement en HTTPS, au seul serveur du calendrier. Si votre service le permet, préférez un mot de passe d\'application.') }}</p>
      </div>
      <p v-if="error" class="error-text">{{ error }}</p>
      <button class="btn primary" type="submit" :disabled="busy">{{ busy ? $t('Vérification…') : $t('Ajouter') }}</button>
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
}
.info {
  flex: 1;
  display: grid;
  gap: 2px;
  min-width: 0;
  font-size: 13px;
}
.info strong {
  font-size: 14.5px;
}
.color {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 50%;
  padding: 0;
  background: none;
  cursor: pointer;
}
.color.big {
  width: 44px;
  height: 38px;
}
.icon-btn.danger {
  color: #fff;
  background: var(--down);
}
.list li {
  flex-wrap: wrap;
}
.auth-edit {
  flex-basis: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--hairline);
}
.auth-actions {
  grid-column: 1 / -1;
  display: flex;
  gap: 8px;
}
.auth-edit .error-text {
  grid-column: 1 / -1;
}
.grid-auth {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.hint {
  grid-column: 1 / -1;
  margin: 0;
  font-size: 12.5px;
}
.icon-btn.active {
  background: var(--accent-soft);
  color: var(--accent);
}
.add {
  display: grid;
  gap: 12px;
  padding-top: 8px;
}
.add h3 {
  font-size: 15px;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
}
.empty {
  justify-content: center;
}
p {
  margin: 0;
}
.add .btn {
  justify-self: start;
}
</style>
