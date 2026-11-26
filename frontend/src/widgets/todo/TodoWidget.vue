<script setup lang="ts">
/**
 * Tâches : une tâche cochée disparaît de la liste mais reste consultable dans « Terminées »,
 * avec sa date de création et sa date de clôture. Cases carrées ou rondes (réglage du widget).
 */
import { PhArrowCounterClockwise, PhCaretDown, PhCheck, PhCheckSquare, PhPlus, PhTrash } from '@phosphor-icons/vue'
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '@/api/client'
import type { TodoItem, Widget } from '@/api/types'
import { intlLocale, t, tn } from '@/i18n'
import WidgetHeader from '../WidgetHeader.vue'

const props = defineProps<{ widget: Widget; editing: boolean }>()
const items = ref<TodoItem[]>([])
const error = ref('')
const draft = ref('')
const showDone = ref(false)
const leaving = ref(new Set<string>()) // tâches qui viennent d'être cochées (animation de sortie)
const editingId = ref<string | null>(null)
const editText = ref('')
const confirmPurge = ref(false)

const round = computed(() => (props.widget.config as { shape?: string }).shape === 'round')
const open = computed(() => items.value.filter((i) => !i.done_at || leaving.value.has(i.id)).sort((a, b) => a.position - b.position))
const done = computed(() =>
  items.value.filter((i) => i.done_at && !leaving.value.has(i.id)).sort((a, b) => b.done_at!.localeCompare(a.done_at!)),
)
const subtitle = computed(() =>
  open.value.length ? tn(open.value.length, '{n} tâche à faire', '{n} tâches à faire') : t('Rien à faire'),
)

const base = computed(() => `/api/v1/todo?widget=${encodeURIComponent(props.widget.id)}`)
async function load() {
  try {
    items.value = await api<TodoItem[]>(base.value)
    error.value = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}
onMounted(load)
watch(() => props.widget.id, load)

async function add() {
  const text = draft.value.trim()
  if (!text) return
  draft.value = ''
  try {
    items.value.push(await api<TodoItem>('/api/v1/todo', { method: 'POST', json: { widget: props.widget.id, text } }))
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    draft.value = text
  }
}

function replace(it: TodoItem) {
  const i = items.value.findIndex((x) => x.id === it.id)
  if (i >= 0) items.value[i] = it
}

async function setDone(it: TodoItem, value: boolean) {
  try {
    const updated = await api<TodoItem>(`/api/v1/todo/${it.id}`, { method: 'PATCH', json: { done: value } })
    if (value) {
      // La case se coche, puis la tâche quitte la liste en douceur
      leaving.value = new Set([...leaving.value, it.id])
      replace(updated)
      window.setTimeout(() => {
        const next = new Set(leaving.value)
        next.delete(it.id)
        leaving.value = next
      }, 650)
    } else replace(updated)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

function startEdit(it: TodoItem) {
  if (props.editing) return
  editingId.value = it.id
  editText.value = it.text
}
async function commitEdit(it: TodoItem) {
  const text = editText.value.trim()
  editingId.value = null
  if (!text || text === it.text) return
  try {
    replace(await api<TodoItem>(`/api/v1/todo/${it.id}`, { method: 'PATCH', json: { text } }))
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function remove(it: TodoItem) {
  try {
    await api(`/api/v1/todo/${it.id}`, { method: 'DELETE' })
    items.value = items.value.filter((x) => x.id !== it.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function purgeDone() {
  if (!confirmPurge.value) {
    confirmPurge.value = true
    return
  }
  confirmPurge.value = false
  try {
    await api(`${base.value}&done_only=true`, { method: 'DELETE' })
    items.value = items.value.filter((x) => !x.done_at)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

const fmt = (iso: string) =>
  new Date(iso).toLocaleString(intlLocale.value, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
</script>

<template>
  <div class="todo" :class="{ round }">
    <WidgetHeader :title="widget.title || $t('Tâches')" :subtitle="subtitle">
      <template #icon><PhCheckSquare :size="22" /></template>
      <template #right><span /></template>
    </WidgetHeader>

    <form class="add" @submit.prevent="add">
      <input v-model="draft" class="input" maxlength="500" :placeholder="$t('Ajouter une tâche…')" :aria-label="$t('Nouvelle tâche')" :disabled="editing" />
      <button class="icon-btn" type="submit" :aria-label="$t('Ajouter')" :disabled="editing || !draft.trim()"><PhPlus :size="18" weight="bold" /></button>
    </form>

    <div class="scroll">
      <TransitionGroup tag="ul" name="todo" class="list">
        <li v-for="it in open" :key="it.id" class="item" :class="{ checked: leaving.has(it.id) }">
          <button
            type="button"
            class="box"
            role="checkbox"
            :aria-checked="leaving.has(it.id)"
            :aria-label="$t('Terminer : {text}', { text: it.text })"
            :disabled="editing || leaving.has(it.id)"
            @click="setDone(it, true)"
          >
            <PhCheck :size="13" weight="bold" />
          </button>
          <input
            v-if="editingId === it.id"
            v-model="editText"
            class="edit"
            maxlength="500"
            :aria-label="$t('Modifier la tâche')"
            @keydown.enter.prevent="commitEdit(it)"
            @keydown.escape="editingId = null"
            @blur="commitEdit(it)"
          />
          <span v-else class="text" :title="$t('Créée le {date}', { date: fmt(it.created_at) })" @dblclick="startEdit(it)">{{ it.text }}</span>
        </li>
      </TransitionGroup>
      <p v-if="!open.length && !error" class="empty faint">{{ $t('Aucune tâche en cours.') }}</p>

      <div v-if="done.length" class="done-block">
        <button type="button" class="done-toggle" :aria-expanded="showDone" @click="showDone = !showDone">
          <PhCaretDown :size="13" weight="bold" class="caret" :class="{ open: showDone }" />
          {{ tn(done.length, '{n} tâche terminée', '{n} tâches terminées') }}
        </button>
        <ul v-if="showDone" class="list done">
          <li v-for="it in done" :key="it.id" class="item">
            <button
              type="button"
              class="box on"
              role="checkbox"
              aria-checked="true"
              :aria-label="$t('Rouvrir : {text}', { text: it.text })"
              :title="$t('Rouvrir')"
              :disabled="editing"
              @click="setDone(it, false)"
            >
              <PhCheck :size="13" weight="bold" />
            </button>
            <div class="meta">
              <span class="text">{{ it.text }}</span>
              <span class="dates faint">
                {{ $t('Créée le {date}', { date: fmt(it.created_at) }) }} · {{ $t('terminée le {date}', { date: fmt(it.done_at!) }) }}
              </span>
            </div>
            <button type="button" class="icon-btn tiny" :aria-label="$t('Supprimer : {text}', { text: it.text })" :title="$t('Supprimer')" :disabled="editing" @click="remove(it)">
              <PhTrash :size="15" />
            </button>
          </li>
          <li class="purge">
            <button type="button" class="link" :class="{ danger: confirmPurge }" :disabled="editing" @click="purgeDone" @blur="confirmPurge = false">
              <PhArrowCounterClockwise v-if="!confirmPurge" :size="13" />
              {{ confirmPurge ? $t('Confirmer : supprimer définitivement les tâches terminées') : $t('Vider les tâches terminées') }}
            </button>
          </li>
        </ul>
      </div>
    </div>
    <p v-if="error" class="error-text small">{{ error }}</p>
  </div>
</template>

<style scoped>
.todo {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}
.add {
  display: flex;
  gap: 6px;
  align-items: center;
}
.add .input {
  flex: 1;
  height: 36px;
  min-width: 0;
}
.scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  margin: 0 -6px;
  padding: 0 6px;
  scrollbar-width: thin;
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 2px;
}
.item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 2px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.35;
}
.box {
  flex: none;
  width: 20px;
  height: 20px;
  margin-top: 0;
  padding: 0;
  display: grid;
  place-items: center;
  border-radius: 6px;
  border: 1.6px solid var(--text-3);
  background: transparent;
  color: transparent;
  transition: background var(--dur-fast), border-color var(--dur-fast), color var(--dur-fast), transform var(--dur-fast);
}
.round .box {
  border-radius: 50%;
}
.box:hover:not(:disabled) {
  border-color: var(--accent);
  transform: scale(1.06);
}
.checked .box,
.box.on {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
.text {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  cursor: text;
  transition: color var(--dur), opacity var(--dur);
}
.checked .text {
  color: var(--text-3);
  text-decoration: line-through;
}
.edit {
  flex: 1;
  min-width: 0;
  font: inherit;
  border: none;
  border-bottom: 1px solid var(--accent);
  background: transparent;
  color: inherit;
  outline: none;
  padding: 0;
}
.empty {
  margin: 6px 2px;
  font-size: 13.5px;
}
.done-block {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--hairline);
}
.done-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: none;
  padding: 4px 2px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-2);
}
.caret {
  transform: rotate(-90deg);
  transition: transform var(--dur-fast);
}
.caret.open {
  transform: none;
}
.done .text {
  color: var(--text-2);
  text-decoration: line-through;
}
.meta {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 2px;
}
.dates {
  font-size: 11.5px;
}
.tiny {
  width: 28px;
  height: 28px;
  flex: none;
  opacity: 0.6;
}
.tiny:hover {
  opacity: 1;
}
.purge {
  padding: 6px 2px 2px;
}
.link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: none;
  background: none;
  padding: 0;
  font-size: 12.5px;
  color: var(--text-2);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.link.danger {
  color: var(--down);
  font-weight: 600;
}
.small {
  margin: 0;
  font-size: 12.5px;
}
.todo-leave-active {
  transition: opacity 0.35s var(--ease), transform 0.35s var(--ease);
}
.todo-leave-to {
  opacity: 0;
  transform: translateX(12px);
}
.todo-enter-active {
  transition: opacity 0.25s var(--ease), transform 0.25s var(--ease);
}
.todo-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}
@media (prefers-reduced-motion: reduce) {
  .todo-leave-active,
  .todo-enter-active {
    transition: none;
  }
}
</style>
