<script setup lang="ts">
import { PhDownloadSimple, PhUploadSimple } from '@phosphor-icons/vue'
import { ref } from 'vue'
import { useLanding } from '@/stores/landing'
import { t } from '@/i18n'

const store = useLanding()
const fileInput = ref<HTMLInputElement>()
const message = ref('')
const error = ref('')
const confirmReset = ref(false)

async function importFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  message.value = error.value = ''
  try {
    if (file.size > 256 * 1024) throw new Error(t('Fichier trop volumineux'))
    await store.importDocument(JSON.parse(await file.text()))
    message.value = t('Disposition importée.')
  } catch (err) {
    error.value = err instanceof SyntaxError ? "Ce fichier n'est pas un JSON valide." : err instanceof Error ? err.message : String(err)
  } finally {
    if (fileInput.value) fileInput.value.value = ''
  }
}

async function reset() {
  if (!confirmReset.value) {
    confirmReset.value = true
    return
  }
  confirmReset.value = false
  await store.reset()
  message.value = t('Disposition par défaut restaurée.')
}
</script>

<template>
  <section class="sec">
    <h2>{{ $t('Disposition de la Home') }}</h2>
    <p class="muted">
      {{ $t('Sauvegardez ou transférez la disposition de votre page d\'accueil (format JSON versionné). Le fichier ne contient aucun secret : seulement l\'emplacement et les réglages des widgets.') }}
    </p>
    <div class="actions">
      <a class="btn" href="/api/v1/landing/layout/export" download><PhDownloadSimple :size="16" /> {{ $t('Exporter') }}</a>
      <button class="btn" type="button" @click="fileInput?.click()"><PhUploadSimple :size="16" /> {{ $t('Importer') }}</button>
      <input ref="fileInput" type="file" accept="application/json,.json" hidden @change="importFile" />
      <button class="btn" :class="{ danger: confirmReset }" type="button" @click="reset" @blur="confirmReset = false">
        {{ confirmReset ? $t('Confirmer la réinitialisation ?') : $t('Réinitialiser') }}
      </button>
    </div>
    <p v-if="message" class="muted">{{ message }}</p>
    <p v-if="error" class="error-text">{{ error }}</p>
  </section>
</template>

<style scoped>
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
p {
  margin: 0;
}
</style>
