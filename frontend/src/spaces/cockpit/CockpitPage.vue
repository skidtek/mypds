<script setup lang="ts">
import { PhCaretUp, PhCheck, PhPencilSimple, PhPlus, PhTrash, PhCaretLeft, PhCaretRight, PhArrowCounterClockwise } from '@phosphor-icons/vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TopBar from '@/app/TopBar.vue'
import { navigateInstant } from '@/app/transition'
import { useCockpit } from '@/stores/cockpit'
import { useSession } from '@/stores/session'
import CockpitRow from './CockpitRow.vue'
import DemoBadge from './DemoBadge.vue'
import TileEditor from './TileEditor.vue'
import { intlLocale, t } from '@/i18n'
import { since } from '@/design-system/time'
import { taskPhrase } from './labels'

const route = useRoute()
const router = useRouter()
const session = useSession()
const store = useCockpit()
const loadError = ref('')
const editor = ref<{ groupId: string; rowId?: string; tileId?: string } | null>(null)
const renaming = ref<string | null>(null)
const renameValue = ref('')
const confirmGroup = ref<string | null>(null)
const confirmReset = ref(false)
let poll: number | undefined

const groups = computed(() => store.doc?.groups ?? [])
const current = computed(() => groups.value.find((g) => g.id === route.params.group) ?? groups.value[0])
const editingTile = computed(() => {
  if (!editor.value?.tileId) return undefined
  for (const g of groups.value) for (const r of g.rows) for (const t of r.tiles) if (t.id === editor.value.tileId) return t
  return undefined
})

const hello = computed(() => {
  const h = new Date().getHours()
  return h < 5 || h >= 18 ? t('Bonsoir') : t('Bonjour')
})
const today = computed(() =>
  new Date().toLocaleDateString(intlLocale.value, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
)
const alertCount = computed(() => store.alerts.length)

/** Onglet contenant une tuile de ce type (l'onglet affiché en priorité). */
function groupWith(type: string) {
  const has = (g: (typeof groups.value)[number]) => g.rows.some((r) => r.tiles.some((t) => t.type === type))
  return current.value && has(current.value) ? current.value : groups.value.find(has)
}
const hasTile = (type: string) => !!groupWith(type)

/** Indicateurs d'en-tête : ouvre l'onglet de la tuile, la fait défiler à l'écran et la met en évidence. */
async function goToTile(type: 'alerts' | 'activity') {
  const g = groupWith(type)
  if (!g) return
  if (g.id !== current.value?.id) await router.replace({ name: 'cockpit', params: { group: g.id } })
  await nextTick()
  const el = document.querySelector<HTMLElement>(`[data-tile-type="${type}"]`)
  if (!el) return
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'center' })
  el.classList.remove('spotlight')
  void el.offsetWidth // relance l'animation si on clique deux fois
  el.classList.add('spotlight')
  window.setTimeout(() => el.classList.remove('spotlight'), 1800)
}

// Dernière activité (tâche la plus récente) affichée dans l'en-tête
const lastTask = computed(() => store.tasks[0])
const lastTaskWhen = computed(() => (lastTask.value ? since(new Date((lastTask.value.end ?? lastTask.value.start) * 1000).toISOString()) : ''))

function selectGroup(id: string) {
  void router.replace({ name: 'cockpit', params: { group: id } })
}

onMounted(async () => {
  try {
    await Promise.all([store.load(), store.loadSnapshots()])
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e)
  }
  poll = window.setInterval(() => document.visibilityState === 'visible' && void store.loadSnapshots(), 15000)
})
onBeforeUnmount(() => {
  window.clearInterval(poll)
  void store.flush()
  store.editing = false
})
watch(
  () => route.params.group,
  () => (renaming.value = null),
)

const back = () => void navigateInstant(router, '/')

function startRename(id: string, title: string) {
  renaming.value = id
  renameValue.value = title
}
function commitRename() {
  if (renaming.value) store.renameGroup(renaming.value, renameValue.value)
  renaming.value = null
}
function addGroup() {
  const id = store.addGroup(t('Nouvel onglet'))
  selectGroup(id)
  startRename(id, t('Nouvel onglet'))
}
function removeGroup(id: string) {
  if (confirmGroup.value !== id) {
    confirmGroup.value = id
    return
  }
  store.removeGroup(id)
  confirmGroup.value = null
  selectGroup(groups.value[0]!.id)
}
async function reset() {
  if (!confirmReset.value) {
    confirmReset.value = true
    return
  }
  confirmReset.value = false
  await store.reset()
}
async function done() {
  store.editing = false
  await store.flush()
}
const statusText = computed(
  () =>
    ({
      idle: t('Modifications enregistrées automatiquement'),
      saving: t('Enregistrement…'),
      saved: t('Modifications enregistrées'),
      error: t('Échec : {error}', { error: store.error }),
      conflict: t('Modifiée ailleurs : rechargez la page'),
    })[store.status],
)
</script>

<template>
  <div class="cockpit">
    <TopBar
      editable
      :editing="store.editing"
      :edit-label="store.editing ? $t('Terminer') : $t('Modifier le Cockpit')"
      settings-section="cockpit"
      :settings-label="$t('Réglages du Cockpit')"
      @edit="store.editing ? done() : (store.editing = true)"
    >
      <button class="up icon-btn" type="button" :aria-label="$t('Revenir à l\'accueil')" :title="$t('Revenir à l\'accueil')" @click="back">
        <PhCaretUp :size="20" weight="bold" />
      </button>
    </TopBar>
    <main class="content">
      <section class="hero glass">
        <div>
          <h1>{{ hello }} {{ session.me?.display_name }}</h1>
          <p class="date">{{ today }}</p>
        </div>
        <div class="chips">
          <DemoBadge v-if="store.anyDemo" />
          <button
            v-if="lastTask"
            type="button"
            class="chip activity-chip"
            :disabled="!hasTile('activity')"
            :title="`${taskPhrase(lastTask)} — ${lastTaskWhen}`"
            :aria-label="$t('Dernière activité : {text}, {when}. Afficher les activités', { text: taskPhrase(lastTask), when: lastTaskWhen })"
            @click="goToTile('activity')"
          >
            <span class="dot" :class="lastTask.state" />
            <span class="act-text">{{ taskPhrase(lastTask) }}</span>
            <span class="faint act-when">{{ lastTaskWhen }}</span>
          </button>
          <button
            v-if="store.snapshots.length"
            type="button"
            class="chip alert-chip"
            :class="{ alert: alertCount }"
            :aria-label="alertCount ? $tn(alertCount, '{n} alerte : afficher', '{n} alertes : afficher') : $t('Aucun problème détecté')"
            :disabled="!hasTile('alerts')"
            :title="hasTile('alerts') ? undefined : $t('Ajoutez la tuile Alertes au Cockpit pour les afficher')"
            @click="goToTile('alerts')"
          >
            <span v-if="alertCount" class="badge-count">{{ alertCount > 99 ? '99+' : alertCount }}</span>
            <span v-else class="dot ok" />
            {{ alertCount ? (alertCount > 1 ? $t('Alertes') : $t('Alerte')) : $t('Aucun problème détecté') }}
          </button>
          <span v-if="store.overview.total" class="chip">{{ $tn(store.overview.total, '{n} service', '{n} services') }}</span>
        </div>
      </section>

      <p v-if="loadError" class="glass err">{{ $t('Impossible de charger le Cockpit : {error}', { error: loadError }) }}</p>

      <template v-else-if="store.doc && current">
        <nav class="tabs" :aria-label="$t('Onglets du Cockpit')">
          <div class="tabs-inner glass">
            <template v-for="(g, i) in groups" :key="g.id">
              <form v-if="renaming === g.id" class="rename" @submit.prevent="commitRename">
                <input v-model="renameValue" class="input" maxlength="40" :aria-label="$t('Nom de l\'onglet')" autofocus @blur="commitRename" />
              </form>
              <button
                v-else
                type="button"
                class="tab"
                :aria-current="g.id === current.id ? 'page' : undefined"
                @click="selectGroup(g.id)"
                @dblclick="store.editing && startRename(g.id, g.title)"
              >
                {{ g.title }}
              </button>
              <span v-if="store.editing && g.id === current.id && renaming !== g.id" class="tab-tools">
                <button type="button" class="mini" :aria-label="$t('Déplacer l\'onglet à gauche')" :disabled="i === 0" @click="store.moveGroup(g.id, -1)"><PhCaretLeft :size="13" /></button>
                <button type="button" class="mini" :aria-label="$t('Renommer l\'onglet')" @click="startRename(g.id, g.title)"><PhPencilSimple :size="13" /></button>
                <button type="button" class="mini" :aria-label="$t('Déplacer l\'onglet à droite')" :disabled="i === groups.length - 1" @click="store.moveGroup(g.id, 1)"><PhCaretRight :size="13" /></button>
                <button v-if="groups.length > 1" type="button" class="mini" :class="{ danger: confirmGroup === g.id }" :aria-label="confirmGroup === g.id ? $t('Confirmer la suppression de l\'onglet') : $t('Supprimer l\'onglet')" @click="removeGroup(g.id)" @blur="confirmGroup = null"><PhTrash :size="13" /></button>
              </span>
            </template>
            <button v-if="store.editing" type="button" class="tab add" :aria-label="$t('Ajouter un onglet')" @click="addGroup"><PhPlus :size="14" /></button>
          </div>
        </nav>

        <div class="group" role="region" :aria-label="current.title">
          <CockpitRow
            v-for="(r, i) in current.rows"
            :key="r.id"
            :row="r"
            :group-id="current.id"
            :index="i"
            :count="current.rows.length"
            @add-tile="editor = { groupId: current.id, rowId: r.id }"
            @configure="(tileId) => (editor = { groupId: current!.id, tileId })"
          />
          <div v-if="!current.rows.some((r) => r.tiles.length) && !store.editing" class="empty glass">
            <p>{{ $t('Cet onglet est vide.') }}</p>
            <button class="btn primary" type="button" @click="store.editing = true">{{ $t('Modifier le Cockpit') }}</button>
          </div>
          <button v-if="store.editing" class="btn add-row" type="button" @click="store.addRow(current.id)"><PhPlus :size="15" /> {{ $t('Ajouter une ligne') }}</button>
        </div>
      </template>
    </main>

    <div v-if="store.editing" class="toolbar glass glass-strong" role="toolbar" :aria-label="$t('Modifier le Cockpit')">
      <div class="status">
        <strong>{{ $t('Modifier le Cockpit') }}</strong>
        <span :class="{ 'error-text': store.status === 'error' || store.status === 'conflict' }">{{ statusText }}</span>
      </div>
      <div class="tools">
        <button class="btn small" :class="{ danger: confirmReset }" type="button" @click="reset" @blur="confirmReset = false">
          <PhArrowCounterClockwise :size="15" /> {{ confirmReset ? $t('Confirmer ?') : $t('Réinitialiser') }}
        </button>
        <button class="btn small primary" type="button" @click="done"><PhCheck :size="15" weight="bold" /> {{ $t('Terminé') }}</button>
      </div>
    </div>

    <TileEditor v-if="editor" :group-id="editor.groupId" :row-id="editor.rowId" :tile="editingTile" @close="editor = null" />
  </div>
</template>

<style scoped>
.cockpit {
  min-height: 100dvh;
}
.content {
  max-width: 1240px;
  margin: 0 auto;
  padding: 4px 32px 120px;
  display: grid;
  gap: 18px;
}
.hero {
  padding: 28px 30px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.hero h1 {
  font-size: 28px;
  font-weight: 700;
}
.date {
  margin: 6px 0 0;
  color: var(--text-2);
}
.date::first-letter {
  text-transform: uppercase;
}
.chips {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.alert-chip {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  flex: none;
  cursor: pointer;
  height: 30px;
  gap: 8px;
  font-family: inherit;
  color: var(--text-1);
}
.alert-chip.alert {
  padding-left: 4px;
}
.alert-chip:disabled,
.activity-chip:disabled {
  cursor: default;
}
.activity-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 30px;
  max-width: min(420px, 40vw);
  font-family: inherit;
  color: var(--text-1);
  cursor: pointer;
}
.act-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.act-when {
  flex: none;
  font-size: 12px;
}
.activity-chip .dot {
  flex: none;
}
.activity-chip .dot.ok {
  background: var(--ok);
}
.activity-chip .dot.running {
  background: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
.activity-chip .dot.warning {
  background: var(--warn);
}
.activity-chip .dot.error {
  background: var(--down);
}
/* Tuile atteinte depuis l'en-tête : halo bref pour la repérer */
:global([data-tile-type].spotlight > *) {
  animation: spotlight 1.8s var(--ease);
}
@keyframes spotlight {
  0%,
  100% {
    box-shadow: var(--shadow-card, none);
  }
  20%,
  60% {
    box-shadow: 0 0 0 3px var(--accent), 0 0 32px 4px color-mix(in srgb, var(--accent) 45%, transparent);
  }
}
@media (max-width: 699px) {
  .activity-chip {
    max-width: 100%;
  }
}
@media (prefers-reduced-motion: reduce) {
  :global([data-tile-type].spotlight > *) {
    animation: none;
    outline: 3px solid var(--accent);
  }
}
.badge-count {
  min-width: 22px;
  height: 22px;
  padding: 0 5px;
  border-radius: var(--radius-pill);
  background: var(--down);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 11.5px;
  font-weight: 700;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--down) 25%, transparent);
}
.tabs {
  display: flex;
  justify-content: center;
  position: sticky;
  top: 8px;
  z-index: 20;
}
.tabs-inner {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px;
  border-radius: var(--radius-pill);
  max-width: 100%;
  overflow-x: auto;
  scrollbar-width: none;
}
.tab {
  height: 34px;
  padding: 0 16px;
  border: none;
  border-radius: var(--radius-pill);
  background: transparent;
  font-weight: 600;
  font-size: 14px;
  color: var(--text-2);
  white-space: nowrap;
}
.tab:hover {
  color: var(--text-1);
}
.tab[aria-current='page'] {
  background: var(--surface-strong);
  color: var(--text-1);
  box-shadow: 0 1px 6px rgb(0 0 0 / 0.1);
}
.tab.add {
  padding: 0 12px;
}
.tab-tools {
  display: inline-flex;
  gap: 1px;
}
.mini {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 50%;
  background: transparent;
  display: grid;
  place-items: center;
  color: var(--text-2);
}
.mini:hover:not(:disabled) {
  background: var(--accent-soft);
}
.mini:disabled {
  opacity: 0.3;
}
.mini.danger {
  background: var(--down);
  color: #fff;
}
.rename .input {
  height: 34px;
  width: 160px;
  padding: 0 12px;
  border-radius: var(--radius-pill);
}
.group {
  display: grid;
  gap: 18px;
}
.empty {
  padding: 40px;
  display: grid;
  justify-items: center;
  gap: 12px;
  color: var(--text-2);
}
.empty p {
  margin: 0;
}
.add-row {
  justify-self: center;
}
.err {
  padding: 20px;
}
.toolbar {
  position: fixed;
  left: 50%;
  bottom: calc(18px + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 10px 10px 10px 20px;
  border-radius: 22px;
  box-shadow: var(--shadow-float);
  max-width: calc(100vw - 24px);
}
.status {
  display: grid;
  font-size: 12.5px;
}
.status span {
  color: var(--text-2);
}
.tools {
  display: flex;
  gap: 6px;
}
@media (max-width: 699px) {
  .content {
    padding: 0 14px 120px;
  }
  .hero {
    padding: 22px 20px;
  }
  .hero h1 {
    font-size: 23px;
  }
  .tabs {
    justify-content: flex-start;
  }
}
</style>
