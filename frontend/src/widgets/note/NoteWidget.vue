<script setup lang="ts">
/**
 * Post-it à intercalaires : un onglet par note, chacun avec sa couleur et sa texture.
 * Le texte s'enregistre tout seul pendant la frappe.
 */
import { PhPalette, PhPlus, PhTrash } from '@phosphor-icons/vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '@/api/client'
import type { NoteColor, NoteItem, NoteTexture, Widget } from '@/api/types'
import { t, tk } from '@/i18n'

const props = defineProps<{ widget: Widget; editing: boolean }>()
const notes = ref<NoteItem[]>([])
const activeId = ref<string | null>(null)
const error = ref('')
const styling = ref(false)
const confirmDelete = ref(false)
const saving = ref<'idle' | 'saving' | 'saved'>('idle')

const COLORS: { id: NoteColor; name: string }[] = [
  { id: 'yellow', name: tk('Jaune') },
  { id: 'pink', name: tk('Rose') },
  { id: 'green', name: tk('Vert') },
  { id: 'blue', name: tk('Bleu') },
  { id: 'orange', name: tk('Orange') },
  { id: 'purple', name: tk('Violet') },
]
const TEXTURES: { id: NoteTexture; name: string }[] = [
  { id: 'plain', name: tk('Lisse') },
  { id: 'paper', name: tk('Papier') },
  { id: 'lined', name: tk('Ligné') },
  { id: 'grid', name: tk('Quadrillé') },
]

const storeKey = computed(() => `mypds.note.${props.widget.id}`)
const active = computed(() => notes.value.find((n) => n.id === activeId.value) ?? notes.value[0])
const tabLabel = (n: NoteItem, i: number) => n.title || n.body.split('\n')[0]?.trim().slice(0, 24) || t('Note {n}', { n: i + 1 })

async function load() {
  try {
    notes.value = await api<NoteItem[]>(`/api/v1/notes?widget=${encodeURIComponent(props.widget.id)}`)
    const remembered = localStorage.getItem(storeKey.value)
    activeId.value = notes.value.some((n) => n.id === remembered) ? remembered : (notes.value[0]?.id ?? null)
    error.value = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}
onMounted(load)
watch(() => props.widget.id, load)
watch(activeId, (id) => {
  flush() // texte en attente du post-it précédent
  if (id) localStorage.setItem(storeKey.value, id)
  styling.value = false
  confirmDelete.value = false
})

async function addNote() {
  try {
    // Le nouveau post-it reprend la couleur suivante, pour distinguer les intercalaires
    const color = COLORS[notes.value.length % COLORS.length]!.id
    const n = await api<NoteItem>('/api/v1/notes', { method: 'POST', json: { widget: props.widget.id, color } })
    notes.value.push(n)
    activeId.value = n.id
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function patch(n: NoteItem, change: Partial<Pick<NoteItem, 'title' | 'body' | 'color' | 'texture'>>) {
  saving.value = 'saving'
  try {
    const updated = await api<NoteItem>(`/api/v1/notes/${n.id}`, { method: 'PATCH', json: change })
    const i = notes.value.findIndex((x) => x.id === n.id)
    // On garde le texte local s'il a changé entre-temps (frappe en cours)
    if (i >= 0) notes.value[i] = { ...updated, body: notes.value[i]!.body, title: notes.value[i]!.title }
    saving.value = 'saved'
    error.value = ''
  } catch (e) {
    saving.value = 'idle'
    error.value = e instanceof Error ? e.message : String(e)
  }
}

// Enregistrement automatique du texte (après une courte pause de frappe)
let timer: number | undefined
let pending: { note: NoteItem; change: Partial<NoteItem> } | null = null
function queue(n: NoteItem, change: Partial<NoteItem>) {
  Object.assign(n, change)
  pending = { note: n, change: { ...(pending?.note.id === n.id ? pending.change : {}), ...change } }
  saving.value = 'saving'
  window.clearTimeout(timer)
  timer = window.setTimeout(flush, 700)
}
function flush() {
  window.clearTimeout(timer)
  if (!pending) return
  const { note, change } = pending
  pending = null
  void patch(note, change)
}
onBeforeUnmount(flush)

async function removeActive() {
  const n = active.value
  if (!n) return
  if (!confirmDelete.value) {
    confirmDelete.value = true
    return
  }
  try {
    await api(`/api/v1/notes/${n.id}`, { method: 'DELETE' })
    const i = notes.value.findIndex((x) => x.id === n.id)
    notes.value.splice(i, 1)
    activeId.value = notes.value[Math.max(0, i - 1)]?.id ?? null
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

function onTabKey(e: KeyboardEvent, i: number) {
  const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
  if (!d || !notes.value.length) return
  e.preventDefault()
  const next = notes.value[(i + d + notes.value.length) % notes.value.length]!
  activeId.value = next.id
  ;(document.getElementById(`tab-${next.id}`) as HTMLElement | null)?.focus()
}
</script>

<template>
  <div class="notes">
    <div class="tabs" role="tablist" :aria-label="$t('Post-it')">
      <button
        v-for="(n, i) in notes"
        :id="`tab-${n.id}`"
        :key="n.id"
        type="button"
        role="tab"
        class="tab"
        :class="`c-${n.color}`"
        :aria-selected="n.id === active?.id"
        :tabindex="n.id === active?.id ? 0 : -1"
        :title="tabLabel(n, i)"
        @click="activeId = n.id"
        @keydown="onTabKey($event, i)"
      >
        {{ tabLabel(n, i) }}
      </button>
      <button type="button" class="tab add" :aria-label="$t('Nouveau post-it')" :title="$t('Nouveau post-it')" :disabled="editing || notes.length >= 20" @click="addNote">
        <PhPlus :size="14" weight="bold" />
      </button>
    </div>

    <div v-if="active" class="paper" :class="[`c-${active.color}`, `x-${active.texture}`]" role="tabpanel" :aria-labelledby="`tab-${active.id}`">
      <div class="paper-head">
        <input
          class="title"
          :value="active.title"
          maxlength="40"
          :placeholder="$t('Titre')"
          :aria-label="$t('Titre du post-it')"
          :disabled="editing"
          @input="queue(active, { title: ($event.target as HTMLInputElement).value })"
        />
        <span class="state" aria-live="polite">{{ saving === 'saving' ? $t('Enregistrement…') : '' }}</span>
        <button type="button" class="tool" :aria-expanded="styling" :aria-label="$t('Couleur et texture')" :title="$t('Couleur et texture')" :disabled="editing" @click="styling = !styling">
          <PhPalette :size="16" />
        </button>
      </div>
      <div v-if="styling" class="styler">
        <div class="swatches" role="radiogroup" :aria-label="$t('Couleur')">
          <button
            v-for="c in COLORS"
            :key="c.id"
            type="button"
            role="radio"
            class="swatch"
            :class="`c-${c.id}`"
            :aria-checked="active.color === c.id"
            :aria-label="$t(c.name)"
            :title="$t(c.name)"
            @click="patch(active, { color: c.id }); active.color = c.id"
          />
        </div>
        <div class="textures" role="radiogroup" :aria-label="$t('Texture')">
          <button
            v-for="x in TEXTURES"
            :key="x.id"
            type="button"
            role="radio"
            class="texture"
            :class="[`c-${active.color}`, `x-${x.id}`]"
            :aria-checked="active.texture === x.id"
            @click="patch(active, { texture: x.id }); active.texture = x.id"
          >
            {{ $t(x.name) }}
          </button>
        </div>
        <button type="button" class="delete" :class="{ confirm: confirmDelete }" @click="removeActive" @blur="confirmDelete = false">
          <PhTrash :size="14" /> {{ confirmDelete ? $t('Supprimer ce post-it ?') : $t('Supprimer ce post-it') }}
        </button>
      </div>
      <textarea
        class="body"
        :value="active.body"
        maxlength="20000"
        :placeholder="$t('Écrivez ici…')"
        :aria-label="$t('Contenu du post-it')"
        :disabled="editing"
        @input="queue(active, { body: ($event.target as HTMLTextAreaElement).value })"
        @blur="flush"
      />
    </div>
    <div v-else class="empty">
      <button v-if="!error" class="btn small" type="button" :disabled="editing" @click="addNote"><PhPlus :size="14" /> {{ $t('Créer un post-it') }}</button>
    </div>
    <p v-if="error" class="error-text small">{{ error }}</p>
  </div>
</template>

<style scoped>
.notes {
  --yellow: #fde68a;
  --pink: #fbcfe8;
  --green: #bbf7d0;
  --blue: #bfdbfe;
  --orange: #fed7aa;
  --purple: #ddd6fe;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  margin: -4px -6px -6px;
}
.c-yellow {
  --paper: var(--yellow);
}
.c-pink {
  --paper: var(--pink);
}
.c-green {
  --paper: var(--green);
}
.c-blue {
  --paper: var(--blue);
}
.c-orange {
  --paper: var(--orange);
}
.c-purple {
  --paper: var(--purple);
}

/* Intercalaires */
.tabs {
  display: flex;
  gap: 3px;
  padding: 0 8px;
  overflow-x: auto;
  scrollbar-width: none;
  flex: none;
}
.tab {
  flex: 0 1 auto;
  max-width: 130px;
  min-width: 34px;
  height: 28px;
  padding: 0 12px;
  border: none;
  border-radius: 10px 10px 0 0;
  background: color-mix(in srgb, var(--paper, #ddd) 80%, #8a8a8a);
  opacity: 0.92;
  color: #2a2a2a;
  font-size: 12.5px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transform: translateY(4px);
  transition: transform var(--dur-fast), background var(--dur-fast);
}
.tab[aria-selected='true'] {
  background: var(--paper);
  opacity: 1;
  transform: translateY(0);
  box-shadow: 0 -2px 8px -4px rgb(0 0 0 / 0.25);
}
.tab:hover:not([aria-selected='true']) {
  transform: translateY(2px);
}
.tab.add {
  display: grid;
  place-items: center;
  padding: 0 10px;
  background: rgb(var(--surface-rgb) / 0.5);
  color: var(--text-1);
}

/* Papier */
.paper {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-radius: 4px 14px 14px 14px;
  background-color: var(--paper);
  color: #2a2a2a;
  box-shadow: 0 10px 24px -12px rgb(0 0 0 / 0.45), inset 0 -18px 30px -24px rgb(0 0 0 / 0.25);
  padding: 10px 14px 12px;
  --line: 24px;
}
.x-paper {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0.35 0 0 0 0 0.3 0 0 0 0 0.2 0 0 0 0.16 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
.x-lined {
  background-image: linear-gradient(to bottom, transparent calc(var(--line) - 1px), rgb(60 90 160 / 0.28) calc(var(--line) - 1px));
  background-size: 100% var(--line);
  background-position: 0 9px;
}
.x-grid {
  background-image:
    linear-gradient(to bottom, rgb(60 90 160 / 0.18) 1px, transparent 1px),
    linear-gradient(to right, rgb(60 90 160 / 0.18) 1px, transparent 1px);
  background-size: 18px 18px;
}
.paper-head {
  display: flex;
  align-items: center;
  gap: 6px;
}
.title {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  font: inherit;
  font-weight: 700;
  font-size: 14.5px;
  color: inherit;
  padding: 2px 0;
  outline: none;
}
.title::placeholder,
.body::placeholder {
  color: rgb(42 42 42 / 0.45);
}
.state {
  font-size: 11px;
  color: rgb(42 42 42 / 0.6);
}
.tool {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: rgb(255 255 255 / 0.35);
  color: #2a2a2a;
  display: grid;
  place-items: center;
}
.tool:hover {
  background: rgb(255 255 255 / 0.6);
}
.body {
  flex: 1;
  min-height: 0;
  resize: none;
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 14.5px;
  line-height: var(--line);
  padding: 0;
  margin-top: 4px;
  outline: none;
}

/* Choix couleur / texture */
.styler {
  display: grid;
  gap: 8px;
  margin: 6px 0 4px;
  padding: 10px;
  border-radius: 12px;
  background: rgb(255 255 255 / 0.55);
  box-shadow: 0 6px 16px -10px rgb(0 0 0 / 0.4);
}
.swatches,
.textures {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.swatch {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid rgb(0 0 0 / 0.12);
  background: var(--paper);
  padding: 0;
}
.swatch[aria-checked='true'] {
  box-shadow: 0 0 0 2px #fff, 0 0 0 4px #2a2a2a;
}
.texture {
  height: 30px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid rgb(0 0 0 / 0.12);
  background-color: var(--paper);
  color: #2a2a2a;
  font-size: 12px;
  font-weight: 600;
  --line: 9px;
}
.texture.x-grid {
  background-size: 7px 7px;
}
.texture[aria-checked='true'] {
  border-color: #2a2a2a;
  box-shadow: inset 0 0 0 1px #2a2a2a;
}
.delete {
  justify-self: start;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: none;
  background: none;
  padding: 2px 0;
  font-size: 12px;
  color: #7a2a2a;
}
.delete.confirm {
  color: #fff;
  background: var(--down);
  padding: 4px 10px;
  border-radius: 999px;
  font-weight: 600;
}
.empty {
  flex: 1;
  display: grid;
  place-items: center;
}
.small {
  margin: 4px 8px 0;
  font-size: 12.5px;
}
</style>
