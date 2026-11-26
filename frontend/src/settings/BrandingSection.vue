<script setup lang="ts">
import { PhArrowCounterClockwise, PhUploadSimple } from '@phosphor-icons/vue'
import { reactive, ref } from 'vue'
import type { Branding } from '@/api/types'
import { DEFAULT_BRANDING, logoUrl, usePreferences } from '@/stores/preferences'
import { t } from '@/i18n'

const store = usePreferences()
const form = reactive<Branding>({ ...store.branding })
const message = ref('')
const error = ref('')
const logoError = ref('')
const busy = ref(false)
const fileInput = ref<HTMLInputElement>()
const MAX = 512 * 1024

async function save() {
  message.value = error.value = ''
  try {
    await store.saveBranding({ ...form, logo_version: store.branding.logo_version })
    message.value = t('Enregistré.')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}
function restore() {
  Object.assign(form, { ...DEFAULT_BRANDING, logo_version: store.branding.logo_version })
}

async function onFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  logoError.value = ''
  if (file.size > MAX) {
    logoError.value = t('Image trop volumineuse (512 Ko maximum).')
  } else {
    busy.value = true
    try {
      await store.uploadLogo(file)
      form.show_logo = true
    } catch (err) {
      logoError.value = err instanceof Error ? err.message : String(err)
    } finally {
      busy.value = false
    }
  }
  if (fileInput.value) fileInput.value.value = ''
}

async function resetLogo() {
  logoError.value = ''
  try {
    await store.resetLogo()
  } catch (err) {
    logoError.value = err instanceof Error ? err.message : String(err)
  }
}
</script>

<template>
  <section class="sec">
    <h2>{{ $t('Marque') }}</h2>
    <p class="muted">{{ $t('Personnalisez le nom et le logo affichés en haut de la Home et sur la page de connexion. Réglage commun à tous les utilisateurs.') }}</p>

    <div class="field">
      <span>{{ $t('Logo') }}</span>
      <div class="logo-row">
        <img class="preview" :class="{ custom: !!store.branding.logo_version }" :src="logoUrl(store.branding)" :alt="$t('Logo actuel')" width="64" height="64" />
        <div class="logo-actions">
          <div class="buttons">
            <button class="btn" type="button" :disabled="busy" @click="fileInput?.click()">
              <PhUploadSimple :size="16" /> {{ busy ? $t('Import…') : $t('Importer un logo') }}
            </button>
            <button v-if="store.branding.logo_version" class="btn" type="button" @click="resetLogo">
              <PhArrowCounterClockwise :size="16" /> {{ $t('Logo par défaut') }}
            </button>
          </div>
          <p class="faint hint">{{ $t('PNG, JPEG ou WebP, 512 Ko maximum. Image carrée conseillée (256 × 256 px ou plus), fond transparent de préférence. Le logo sert aussi d\'icône d\'onglet.') }}</p>
          <p v-if="logoError" class="error-text">{{ logoError }}</p>
        </div>
      </div>
      <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" hidden @change="onFile" />
      <label class="check"><input v-model="form.show_logo" type="checkbox" /> {{ $t('Afficher le logo') }}</label>
      <div v-if="form.show_logo" class="field">
        <span>{{ $t('Position du logo') }}</span>
        <div class="seg">
          <button type="button" :aria-pressed="(form.logo_position ?? 'top') === 'top'" @click="form.logo_position = 'top'">{{ $t('Au-dessus du titre') }}</button>
          <button type="button" :aria-pressed="form.logo_position === 'left'" @click="form.logo_position = 'left'">{{ $t('À gauche') }}</button>
          <button type="button" :aria-pressed="form.logo_position === 'right'" @click="form.logo_position = 'right'">{{ $t('À droite') }}</button>
        </div>
      </div>
    </div>

    <form class="form" @submit.prevent="save">
      <label class="field"><span>{{ $t('Titre complet') }}</span><input v-model="form.title" class="input" maxlength="60" /></label>
      <label class="field"><span>{{ $t('Titre court') }}</span><input v-model="form.short_title" class="input" maxlength="30" /></label>
      <label class="field"><span>{{ $t('Sous-titre') }}</span><input v-model="form.subtitle" class="input" maxlength="80" /></label>
      <div class="field">
        <span>{{ $t('Affichage du titre') }}</span>
        <div class="seg">
          <button type="button" :aria-pressed="form.display === 'full'" @click="form.display = 'full'">{{ $t('Complet') }}</button>
          <button type="button" :aria-pressed="form.display === 'short'" @click="form.display = 'short'">{{ $t('Court') }}</button>
          <button type="button" :aria-pressed="form.display === 'hidden'" @click="form.display = 'hidden'">{{ $t('Masqué') }}</button>
        </div>
      </div>
      <div class="actions">
        <button class="btn primary" type="submit">{{ $t('Enregistrer') }}</button>
        <button class="btn" type="button" @click="restore">{{ $t('Valeurs par défaut') }}</button>
      </div>
      <p v-if="message" class="muted">{{ message }}</p>
      <p v-if="error" class="error-text">{{ error }}</p>
    </form>
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
.logo-row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.preview {
  width: 64px;
  height: 64px;
  flex: none;
  border-radius: 16px;
  background: rgb(var(--surface-rgb) / 0.6);
  border: 1px solid var(--hairline);
  filter: drop-shadow(0 6px 14px rgb(90 80 200 / 0.2));
}
.preview.custom {
  object-fit: contain;
  padding: 4px;
}
.logo-actions {
  display: grid;
  gap: 8px;
  min-width: 0;
}
.hint {
  font-size: 12.5px;
}
p {
  margin: 0;
}
</style>
