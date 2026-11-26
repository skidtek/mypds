<script setup lang="ts">
import { PhDesktop, PhDeviceMobile, PhTrash, PhUploadSimple, PhUserCircle } from '@phosphor-icons/vue'
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import type { Me, UserSession } from '@/api/types'
import { since } from '@/design-system/time'
import { t } from '@/i18n'
import { usePreferences } from '@/stores/preferences'
import { avatarUrl, useSession } from '@/stores/session'
import AvatarCropper from './AvatarCropper.vue'

const session = useSession()
const store = usePreferences()

// Nom affiché
const name = ref(session.me?.display_name ?? '')
const nameMsg = ref('')
const nameErr = ref('')
async function saveName() {
  nameMsg.value = nameErr.value = ''
  try {
    session.set(await api<Me>('/api/v1/me', { method: 'PATCH', json: { display_name: name.value.trim() } }))
    nameMsg.value = t('Enregistré.')
  } catch (e) {
    nameErr.value = e instanceof Error ? e.message : String(e)
  }
}

// Photo
const fileInput = ref<HTMLInputElement>()
const photoErr = ref('')
const busy = ref(false)
const MAX = 5 * 1024 * 1024
const photo = computed(() => (session.me ? avatarUrl(session.me) : null))
async function onFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (fileInput.value) fileInput.value.value = ''
  if (!file) return
  photoErr.value = ''
  if (file.size > MAX) {
    photoErr.value = t('Image trop volumineuse (5 Mo maximum).')
    return
  }
  cropping.value = file // cadrage avant l'envoi
}
const cropping = ref<File | null>(null)
async function upload(blob: Blob) {
  cropping.value = null
  busy.value = true
  try {
    const body = new FormData()
    body.append('file', blob, blob.type === 'image/webp' ? 'avatar.webp' : 'avatar.jpg')
    session.set(await api<Me>('/api/v1/me/avatar', { method: 'PUT', body }))
  } catch (err) {
    photoErr.value = err instanceof Error ? err.message : String(err)
  } finally {
    busy.value = false
  }
}
async function removePhoto() {
  photoErr.value = ''
  try {
    session.set(await api<Me>('/api/v1/me/avatar', { method: 'DELETE' }))
  } catch (err) {
    photoErr.value = err instanceof Error ? err.message : String(err)
  }
}

// Mot de passe
const pw = ref({ current: '', next: '', confirm: '' })
const pwMsg = ref('')
const pwErr = ref('')
async function changePassword() {
  pwMsg.value = pwErr.value = ''
  if (pw.value.next !== pw.value.confirm) {
    pwErr.value = t('Les deux mots de passe ne correspondent pas.')
    return
  }
  try {
    await api('/api/v1/me/password', { method: 'POST', json: { current: pw.value.current, new: pw.value.next } })
    pw.value = { current: '', next: '', confirm: '' }
    pwMsg.value = t('Mot de passe modifié. Les autres sessions ont été fermées.')
    await loadSessions()
  } catch (e) {
    pwErr.value = e instanceof Error ? e.message : String(e)
  }
}

// Sessions
const sessions = ref<UserSession[]>([])
const sessErr = ref('')
async function loadSessions() {
  try {
    sessions.value = await api<UserSession[]>('/api/v1/me/sessions')
  } catch (e) {
    sessErr.value = e instanceof Error ? e.message : String(e)
  }
}
async function closeSession(s: UserSession) {
  sessErr.value = ''
  try {
    await api(`/api/v1/me/sessions/${s.id}`, { method: 'DELETE' })
    await loadSessions()
  } catch (e) {
    sessErr.value = e instanceof Error ? e.message : String(e)
  }
}
async function closeOthers() {
  for (const s of sessions.value.filter((x) => !x.current)) await closeSession(s)
}
const others = computed(() => sessions.value.filter((s) => !s.current).length)

/** « Firefox · macOS » à partir de l'agent utilisateur (indicatif). */
function device(ua: string | null): string {
  if (!ua) return t('Appareil inconnu')
  const browser = /Edg\//.test(ua) ? 'Edge' : /Firefox\//.test(ua) ? 'Firefox' : /Chrome\//.test(ua) ? 'Chrome' : /Safari\//.test(ua) ? 'Safari' : null
  const os = /iPhone|iPad/.test(ua) ? 'iOS' : /Android/.test(ua) ? 'Android' : /Mac OS X/.test(ua) ? 'macOS' : /Windows/.test(ua) ? 'Windows' : /Linux/.test(ua) ? 'Linux' : null
  return [browser, os].filter(Boolean).join(' · ') || ua.slice(0, 40)
}
const isMobile = (ua: string | null) => !!ua && /Mobile|Android|iPhone/.test(ua)

onMounted(loadSessions)
</script>

<template>
  <section class="sec">
    <h2>{{ $t('Mon profil') }}</h2>
    <p class="muted">{{ $t('Ces réglages ne concernent que votre compte.') }}</p>

    <div class="field">
      <span>{{ $t('Photo') }}</span>
      <div class="photo-row">
        <img v-if="photo" class="avatar" :src="photo" :alt="$t('Photo de profil')" width="72" height="72" />
        <PhUserCircle v-else class="avatar empty" :size="72" weight="fill" />
        <div class="photo-actions">
          <div class="buttons">
            <button class="btn" type="button" :disabled="busy" @click="fileInput?.click()">
              <PhUploadSimple :size="16" /> {{ busy ? $t('Import…') : $t('Choisir une photo') }}
            </button>
            <button v-if="photo" class="btn" type="button" @click="removePhoto">{{ $t('Retirer la photo') }}</button>
          </div>
          <p class="faint hint">{{ $t('PNG, JPEG ou WebP, 5 Mo maximum. Vous pourrez la cadrer avant de l\'enregistrer.') }}</p>
          <p v-if="photoErr" class="error-text">{{ photoErr }}</p>
        </div>
      </div>
      <input ref="fileInput" type="file" accept="image/*" hidden @change="onFile" />
      <AvatarCropper v-if="cropping" :file="cropping" @close="cropping = null" @done="upload" />
    </div>

    <form class="form" @submit.prevent="saveName">
      <label class="field">
        <span>{{ $t('Nom affiché') }}</span>
        <input v-model="name" class="input" maxlength="100" required />
      </label>
      <p class="faint hint">{{ $t('Identifiant de connexion : {username}', { username: session.me?.username ?? '' }) }}</p>
      <div class="actions">
        <button class="btn primary" type="submit" :disabled="!name.trim() || name.trim() === session.me?.display_name">{{ $t('Enregistrer') }}</button>
      </div>
      <p v-if="nameMsg" class="muted">{{ nameMsg }}</p>
      <p v-if="nameErr" class="error-text">{{ nameErr }}</p>
    </form>

    <div class="field">
      <span>{{ $t('Langue') }}</span>
      <div class="seg">
        <button type="button" :aria-pressed="store.prefs.locale === 'auto'" @click="store.update({ locale: 'auto' })">{{ $t('Automatique') }}</button>
        <button type="button" :aria-pressed="store.prefs.locale === 'fr'" lang="fr" @click="store.update({ locale: 'fr' })">Français</button>
        <button type="button" :aria-pressed="store.prefs.locale === 'en'" lang="en" @click="store.update({ locale: 'en' })">English</button>
      </div>
      <p class="faint hint">{{ $t('« Automatique » suit la langue de votre navigateur.') }}</p>
    </div>

    <h3>{{ $t('Mot de passe') }}</h3>
    <form class="form" @submit.prevent="changePassword">
      <input class="visually-hidden" type="text" autocomplete="username" :value="session.me?.username" readonly tabindex="-1" aria-hidden="true" />
      <label class="field">
        <span>{{ $t('Mot de passe actuel') }}</span>
        <input v-model="pw.current" class="input" type="password" autocomplete="current-password" required />
      </label>
      <label class="field">
        <span>{{ $t('Nouveau mot de passe') }}</span>
        <input v-model="pw.next" class="input" type="password" autocomplete="new-password" minlength="12" required />
      </label>
      <label class="field">
        <span>{{ $t('Confirmer le nouveau mot de passe') }}</span>
        <input v-model="pw.confirm" class="input" type="password" autocomplete="new-password" minlength="12" required />
      </label>
      <p class="faint hint">{{ $t('12 caractères minimum. Vos autres sessions seront fermées.') }}</p>
      <div class="actions">
        <button class="btn primary" type="submit">{{ $t('Changer le mot de passe') }}</button>
      </div>
      <p v-if="pwMsg" class="muted">{{ pwMsg }}</p>
      <p v-if="pwErr" class="error-text">{{ pwErr }}</p>
    </form>

    <h3>{{ $t('Sessions ouvertes') }}</h3>
    <ul class="sessions">
      <li v-for="s in sessions" :key="s.id" class="sess">
        <component :is="isMobile(s.user_agent) ? PhDeviceMobile : PhDesktop" :size="22" class="dev-icon" />
        <div class="sess-info">
          <strong>{{ device(s.user_agent) }}</strong>
          <span v-if="s.current" class="badge">{{ $t('Cet appareil') }}</span>
          <span class="faint">{{ [s.ip, $t('active {when}', { when: since(s.last_seen_at) })].filter(Boolean).join(' · ') }}</span>
        </div>
        <button v-if="!s.current" class="icon-btn" type="button" :aria-label="$t('Fermer cette session')" :title="$t('Fermer cette session')" @click="closeSession(s)">
          <PhTrash :size="18" />
        </button>
      </li>
    </ul>
    <div v-if="others" class="actions">
      <button class="btn" type="button" @click="closeOthers">{{ $tn(others, 'Fermer l\'autre session', 'Fermer les {n} autres sessions') }}</button>
    </div>
    <p v-if="sessErr" class="error-text">{{ sessErr }}</p>
  </section>
</template>

<style scoped>
.form {
  display: grid;
  gap: 14px;
}
.actions,
.buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
h3 {
  margin: 10px 0 0;
  font-size: 16px;
  font-weight: 650;
}
.photo-row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.avatar {
  width: 72px;
  height: 72px;
  flex: none;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid var(--hairline);
}
.avatar.empty {
  border: 0;
  color: var(--text-faint, currentColor);
  opacity: 0.6;
}
.photo-actions {
  display: grid;
  gap: 8px;
  min-width: 0;
}
.hint {
  font-size: 12.5px;
}
.sessions {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.sess {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgb(var(--surface-rgb) / 0.45);
  border: 1px solid var(--hairline);
}
.dev-icon {
  flex: none;
  opacity: 0.75;
}
.sess-info {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
  min-width: 0;
  flex: 1;
}
.sess-info .faint {
  flex-basis: 100%;
  font-size: 12.5px;
}
.badge {
  font-size: 11.5px;
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--accent);
  color: white;
}
.sess .icon-btn {
  margin-left: auto;
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}
p {
  margin: 0;
}
</style>
