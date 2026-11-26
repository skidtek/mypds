<script setup lang="ts">
import { PhMagnifyingGlass, PhMapPin } from '@phosphor-icons/vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { CalendarSource, Place, RssCategory, Widget } from '@/api/types'
import GlassDialog from '@/design-system/components/GlassDialog.vue'
import { usePreferences } from '@/stores/preferences'
import { useLanding } from '@/stores/landing'
import { t } from '@/i18n'
import { WIDGET_NAMES } from '@/widgets/names'

const props = defineProps<{ widget: Widget }>()
const emit = defineEmits<{ close: [] }>()
const store = useLanding()
const prefs = usePreferences()
const router = useRouter()

const NAMES = WIDGET_NAMES
const title = ref(props.widget.title ?? '')
const cfg = reactive<Record<string, any>>(structuredClone({ ...props.widget.config }))

// Météo
const q = ref('')
const places = ref<Place[]>([])
const searching = ref(false)
const geoError = ref('')
async function searchPlace() {
  if (q.value.trim().length < 2) return
  searching.value = true
  geoError.value = ''
  try {
    places.value = await api<Place[]>(`/api/v1/weather/geocode?q=${encodeURIComponent(q.value.trim())}`)
    if (!places.value.length) geoError.value = t('Aucun lieu trouvé.')
  } catch (e) {
    geoError.value = e instanceof Error ? e.message : String(e)
  } finally {
    searching.value = false
  }
}
function pick(p: Place) {
  cfg.label = p.name
  cfg.latitude = p.latitude
  cfg.longitude = p.longitude
  places.value = []
  q.value = ''
}

// Agenda / News : listes de sources
const sources = ref<CalendarSource[]>([])
const categories = ref<RssCategory[]>([])
onMounted(async () => {
  if (props.widget.type === 'calendar') sources.value = await api<CalendarSource[]>('/api/v1/calendar/sources')
  if (props.widget.type === 'news') categories.value = await api<RssCategory[]>('/api/v1/rss/categories')
})

function toggleIn(key: 'source_ids' | 'category_ids', id: string, all: string[]) {
  const current: string[] = cfg[key] ?? [...all]
  const next = current.includes(id) ? current.filter((x) => x !== id) : [...current, id]
  cfg[key] = next.length === all.length ? null : next
}
const isOn = (key: 'source_ids' | 'category_ids', id: string) => cfg[key] == null || cfg[key].includes(id)

const canSave = computed(() => props.widget.type !== 'weather' || (cfg.latitude != null && cfg.longitude != null))

function save() {
  store.updateWidget(props.widget.id, { title: title.value.trim() || null, config: { ...cfg } })
  emit('close')
}

function manage(section: string) {
  emit('close')
  void router.push({ name: 'settings', query: { section } })
}
</script>

<template>
  <GlassDialog :title="$t('Configurer — {name}', { name: $t(NAMES[widget.type]) })" @close="emit('close')">
    <label v-if="widget.type !== 'search'" class="field">
      <span>{{ $t('Titre affiché') }}</span>
      <input v-model="title" class="input" maxlength="60" :placeholder="$t(NAMES[widget.type])" />
    </label>

    <template v-if="widget.type === 'search'">
      <p class="muted">
        {{ $t('Moteur actuel : choisissez-le directement dans la barre de recherche. L\'URL personnalisée se règle dans Réglages → Recherche.') }}
      </p>
      <label class="check">
        <input type="checkbox" :checked="prefs.prefs.search_autofocus" @change="prefs.update({ search_autofocus: ($event.target as HTMLInputElement).checked })" />
        {{ $t('Placer le curseur dans la recherche à l\'ouverture') }}
      </label>
    </template>

    <template v-else-if="widget.type === 'weather'">
      <div class="field">
        <span>{{ $t('Ville') }}</span>
        <p v-if="cfg.label" class="current"><PhMapPin :size="15" /> {{ cfg.label }} <span class="faint">({{ Number(cfg.latitude).toFixed(2) }}, {{ Number(cfg.longitude).toFixed(2) }})</span></p>
        <form class="row" @submit.prevent="searchPlace">
          <input v-model="q" class="input" :placeholder="$t('Rechercher une ville…')" :aria-label="$t('Rechercher une ville')" />
          <button class="btn" type="submit" :disabled="searching"><PhMagnifyingGlass :size="15" /> {{ $t('Chercher') }}</button>
        </form>
        <p v-if="geoError" class="error-text">{{ geoError }}</p>
        <ul v-if="places.length" class="places">
          <li v-for="p in places" :key="`${p.latitude},${p.longitude}`">
            <button type="button" @click="pick(p)">
              <strong>{{ p.name }}</strong>
              <span class="muted">{{ [p.admin, p.country].filter(Boolean).join(', ') }}</span>
            </button>
          </li>
        </ul>
      </div>
      <label class="field">
        <span>{{ $t('Jours de prévision (si la carte est assez grande) : {n}', { n: cfg.forecast_days }) }}</span>
        <input v-model.number="cfg.forecast_days" type="range" min="0" max="7" />
      </label>
      <div class="field">
        <span>{{ $t('Unité de température (pour tous les widgets)') }}</span>
        <div class="seg">
          <button type="button" :aria-pressed="prefs.prefs.temperature_unit === 'celsius'" @click="prefs.update({ temperature_unit: 'celsius' })">{{ $t('°C') }}</button>
          <button type="button" :aria-pressed="prefs.prefs.temperature_unit === 'fahrenheit'" @click="prefs.update({ temperature_unit: 'fahrenheit' })">{{ $t('°F') }}</button>
        </div>
      </div>
      <p class="faint credit">{{ $t('Données météo :') }} <a href="https://open-meteo.com" target="_blank" rel="noopener noreferrer">Open-Meteo</a> (CC BY 4.0)</p>
    </template>

    <template v-else-if="widget.type === 'calendar'">
      <div class="field">
        <span>{{ $t('Calendriers affichés') }}</span>
        <p v-if="!sources.length" class="muted">{{ $t('Aucun calendrier.') }} <button class="link" type="button" @click="manage('agenda')">{{ $t('Ajouter un flux ICS') }}</button></p>
        <label v-for="s in sources" :key="s.id" class="check">
          <input type="checkbox" :checked="isOn('source_ids', s.id)" @change="toggleIn('source_ids', s.id, sources.map((x) => x.id))" />
          <span class="dot" :style="{ background: s.color }" /> {{ s.name }}
          <span v-if="!s.enabled" class="faint">{{ $t('(désactivé)') }}</span>
        </label>
      </div>
      <label class="field">
        <span>{{ $t('Horizon : {n} jours', { n: cfg.days_ahead }) }}</span>
        <input v-model.number="cfg.days_ahead" type="range" min="1" max="60" />
      </label>
      <label class="field">
        <span>{{ $t('Nombre maximum d\'événements : {n}', { n: cfg.max_events }) }}</span>
        <input v-model.number="cfg.max_events" type="range" min="1" max="30" />
      </label>
    </template>

    <template v-else-if="widget.type === 'news'">
      <div class="field">
        <span>{{ $t('Catégories affichées') }}</span>
        <p v-if="!categories.length" class="muted">{{ $t('Pas de catégorie : tous vos flux sont affichés.') }}</p>
        <label v-for="c in categories" :key="c.id" class="check">
          <input type="checkbox" :checked="isOn('category_ids', c.id)" @change="toggleIn('category_ids', c.id, categories.map((x) => x.id))" />
          {{ c.name }} <span class="faint">({{ c.feed_count }})</span>
        </label>
        <button class="link" type="button" @click="manage('news')">{{ $t('Gérer mes flux et l\'import OPML') }}</button>
      </div>
      <label class="field">
        <span>{{ $t('Nombre d\'articles : {n}', { n: cfg.count }) }}</span>
        <input v-model.number="cfg.count" type="range" min="3" max="30" />
      </label>
    </template>

    <template v-else-if="widget.type === 'todo'">
      <div class="field">
        <span>{{ $t('Cases à cocher') }}</span>
        <div class="seg">
          <button type="button" :aria-pressed="cfg.shape !== 'round'" @click="cfg.shape = 'square'">{{ $t('Carrées') }}</button>
          <button type="button" :aria-pressed="cfg.shape === 'round'" @click="cfg.shape = 'round'">{{ $t('Rondes') }}</button>
        </div>
      </div>
    </template>

    <template v-else-if="widget.type === 'note'">
      <p class="muted">{{ $t('La couleur et la texture se choisissent pour chaque post-it, directement dans le widget.') }}</p>
    </template>

    <template #footer>
      <button class="btn" type="button" @click="emit('close')">{{ $t('Annuler') }}</button>
      <button class="btn primary" type="button" :disabled="!canSave" @click="save">{{ $t('Enregistrer') }}</button>
    </template>
  </GlassDialog>
</template>

<style scoped>
.row {
  display: flex;
  gap: 8px;
}
.current {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-weight: 600;
}
.places {
  list-style: none;
  margin: 0;
  padding: 4px;
  border-radius: var(--radius-sm);
  background: rgb(var(--surface-rgb) / 0.6);
}
.places button {
  width: 100%;
  display: flex;
  gap: 8px;
  align-items: baseline;
  border: none;
  background: none;
  text-align: left;
  padding: 8px 10px;
  border-radius: 8px;
}
.places button:hover {
  background: var(--accent-soft);
}
.link {
  border: none;
  background: none;
  color: var(--accent);
  padding: 0;
  font-weight: 560;
  justify-self: start;
}
p {
  margin: 0;
}
.credit {
  margin: 0;
  font-size: 12px;
}
</style>
