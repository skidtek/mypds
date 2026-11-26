<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import type { Preferences, SearchEngine } from '@/api/types'
import { usePreferences } from '@/stores/preferences'

const store = usePreferences()
const custom = ref(store.prefs.search_custom_url ?? '')
const error = ref('')
const saved = ref(false)
const ENGINES: { id: SearchEngine; name: string }[] = [
  { id: 'google', name: 'Google' },
  { id: 'bing', name: 'Bing' },
  { id: 'duckduckgo', name: 'DuckDuckGo' },
  { id: 'qwant', name: 'Qwant' },
  { id: 'custom', name: 'URL personnalisée' },
]

async function saveCustom() {
  error.value = ''
  saved.value = false
  try {
    const next = { ...store.prefs, search_custom_url: custom.value.trim() || null }
    if (!next.search_custom_url && next.search_engine === 'custom') next.search_engine = 'google'
    store.prefs = await api<Preferences>('/api/v1/me/preferences', { method: 'PUT', json: next })
    saved.value = true
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}
</script>

<template>
  <section class="sec">
    <h2>{{ $t('Recherche') }}</h2>
    <div class="field">
      <span>{{ $t('Moteur par défaut') }}</span>
      <div class="seg">
        <button
          v-for="e in ENGINES"
          :key="e.id"
          type="button"
          :aria-pressed="store.prefs.search_engine === e.id"
          :disabled="e.id === 'custom' && !store.prefs.search_custom_url"
          @click="store.update({ search_engine: e.id })"
        >
          {{ e.name }}
        </button>
      </div>
    </div>
    <form class="field" @submit.prevent="saveCustom">
      <span>{{ $t('URL de recherche personnalisée (%s = mots-clés)') }}</span>
      <div class="row">
        <input v-model="custom" class="input" :placeholder="$t('https://search.example.org/?q=%s')" inputmode="url" />
        <button class="btn" type="submit">{{ $t('Enregistrer') }}</button>
      </div>
      <p v-if="error" class="error-text">{{ error }}</p>
      <p v-else-if="saved" class="muted">{{ $t('Enregistré.') }}</p>
    </form>
    <label class="check">
      <input type="checkbox" :checked="store.prefs.search_autofocus" @change="store.update({ search_autofocus: ($event.target as HTMLInputElement).checked })" />
      {{ $t('Placer le curseur dans la recherche à l\'ouverture de la page (ordinateur)') }}
    </label>
  </section>
</template>

<style scoped>
.row {
  display: flex;
  gap: 8px;
}
p {
  margin: 0;
}
</style>
