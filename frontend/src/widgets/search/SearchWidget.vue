<script setup lang="ts">
import { PhCaretDown, PhCheck, PhMagnifyingGlass } from '@phosphor-icons/vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { SearchEngine } from '@/api/types'
import { usePreferences } from '@/stores/preferences'
import { t } from '@/i18n'

const props = defineProps<{ editing: boolean }>()
const store = usePreferences()
const query = ref('')
const menuOpen = ref(false)
const input = ref<HTMLInputElement>()
const root = ref<HTMLElement>()

const ENGINES: Record<Exclude<SearchEngine, 'custom'>, { label: string; url: string }> = {
  google: { label: 'Google', url: 'https://www.google.com/search?q=%s' },
  bing: { label: 'Bing', url: 'https://www.bing.com/search?q=%s' },
  duckduckgo: { label: 'DuckDuckGo', url: 'https://duckduckgo.com/?q=%s' },
  qwant: { label: 'Qwant', url: 'https://www.qwant.com/?q=%s' },
}

const options = computed(() => {
  const list: { id: SearchEngine; label: string }[] = Object.entries(ENGINES).map(([id, e]) => ({
    id: id as SearchEngine,
    label: e.label,
  }))
  if (store.prefs.search_custom_url) {
    let host = t('Personnalisé')
    try {
      host = new URL(store.prefs.search_custom_url.replace('%s', 'x')).hostname.replace(/^www\./, '')
    } catch {
      /* URL déjà validée côté serveur */
    }
    list.push({ id: 'custom', label: host })
  }
  return list
})

const engine = computed(() => options.value.find((o) => o.id === store.prefs.search_engine) ?? options.value[0]!)

function urlFor(q: string): string {
  const id = engine.value.id
  const template = id === 'custom' ? store.prefs.search_custom_url! : ENGINES[id].url
  return template.replace('%s', encodeURIComponent(q))
}

function submit() {
  const q = query.value.trim()
  if (!q || props.editing) return
  window.location.assign(urlFor(q))
}

function choose(id: SearchEngine) {
  store.update({ search_engine: id })
  menuOpen.value = false
  input.value?.focus()
}

function onDocClick(e: MouseEvent) {
  if (menuOpen.value && root.value && !root.value.contains(e.target as Node)) menuOpen.value = false
}

onMounted(() => {
  document.addEventListener('click', onDocClick)
  if (store.prefs.search_autofocus && !props.editing && window.matchMedia('(min-width: 700px)').matches) {
    input.value?.focus()
  }
})
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <form ref="root" class="search" role="search" @submit.prevent="submit">
    <PhMagnifyingGlass class="lens" :size="20" aria-hidden="true" />
    <input
      ref="input"
      v-model="query"
      class="q"
      type="search"
      enterkeyhint="search"
      autocomplete="off"
      :placeholder="$t('Rechercher avec {engine}…', { engine: engine.label })"
      :aria-label="$t('Rechercher sur le Web')"
      :tabindex="editing ? -1 : 0"
    />
    <div class="engine">
      <button
        type="button"
        class="engine-btn"
        aria-haspopup="listbox"
        :aria-expanded="menuOpen"
        :aria-label="$t('Moteur de recherche : {engine}. Changer', { engine: engine.label })"
        :tabindex="editing ? -1 : 0"
        @click="menuOpen = !menuOpen"
      >
        <span>{{ engine.label }}</span>
        <PhCaretDown :size="13" weight="bold" />
      </button>
      <ul v-if="menuOpen" class="menu glass glass-strong" role="listbox" :aria-label="$t('Moteur de recherche')">
        <li v-for="o in options" :key="o.id" role="option" :aria-selected="o.id === engine.id">
          <button type="button" @click="choose(o.id)">
            <span>{{ o.label }}</span>
            <PhCheck v-if="o.id === engine.id" :size="15" weight="bold" />
          </button>
        </li>
      </ul>
    </div>
  </form>
</template>

<style scoped>
.search {
  height: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 8px 0 22px;
}
.lens {
  color: var(--text-2);
  flex: none;
}
.q {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: none;
  background: transparent;
  font-size: 16px;
  outline: none;
}
.q:focus-visible {
  box-shadow: none;
}
.q::placeholder {
  color: var(--text-3);
}
.q::-webkit-search-cancel-button {
  display: none;
}
.engine {
  position: relative;
}
.engine-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  padding: 0 14px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--surface-border);
  background: var(--surface-strong);
  font-weight: 600;
  font-size: 14px;
  color: var(--text-1);
}
.menu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  z-index: 30;
  list-style: none;
  margin: 0;
  padding: 6px;
  min-width: 190px;
  border-radius: var(--radius-md);
}
.menu button {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: none;
  background: transparent;
  padding: 9px 12px;
  border-radius: 10px;
  font-size: 14px;
  text-align: left;
}
.menu button:hover {
  background: var(--accent-soft);
}
</style>
