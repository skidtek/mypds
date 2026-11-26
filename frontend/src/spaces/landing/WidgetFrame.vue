<script setup lang="ts">
import { PhDotsSixVertical, PhEyeSlash, PhGearSix, PhTrash } from '@phosphor-icons/vue'
import { computed, ref } from 'vue'
import type { Widget } from '@/api/types'
import { useLanding } from '@/stores/landing'
import CalendarWidget from '@/widgets/calendar/CalendarWidget.vue'
import NewsWidget from '@/widgets/news/NewsWidget.vue'
import NoteWidget from '@/widgets/note/NoteWidget.vue'
import SearchWidget from '@/widgets/search/SearchWidget.vue'
import TodoWidget from '@/widgets/todo/TodoWidget.vue'
import WeatherWidget from '@/widgets/weather/WeatherWidget.vue'
import { t } from '@/i18n'
import { WIDGET_NAMES } from '@/widgets/names'

const props = defineProps<{ widget: Widget }>()
const emit = defineEmits<{ configure: [] }>()
const store = useLanding()
const confirmDelete = ref(false)

const name = computed(() => props.widget.title || t(WIDGET_NAMES[props.widget.type]))
</script>

<template>
  <section class="frame glass" :class="[`t-${widget.type}`, { editing: store.editing }]" :aria-label="name">
    <div class="content" :inert="store.editing || undefined">
      <SearchWidget v-if="widget.type === 'search'" :editing="store.editing" />
      <WeatherWidget v-else-if="widget.type === 'weather'" :widget="widget" :editing="store.editing" @configure="emit('configure')" />
      <CalendarWidget v-else-if="widget.type === 'calendar'" :widget="widget" :editing="store.editing" />
      <NewsWidget v-else-if="widget.type === 'news'" :widget="widget" :editing="store.editing" />
      <TodoWidget v-else-if="widget.type === 'todo'" :widget="widget" :editing="store.editing" />
      <NoteWidget v-else-if="widget.type === 'note'" :widget="widget" :editing="store.editing" />
    </div>

    <div v-if="store.editing" class="edit-bar">
      <span class="handle"><PhDotsSixVertical :size="16" weight="bold" /> {{ name }}</span>
      <span class="actions">
        <button type="button" class="tool" :aria-label="$t('Configurer {name}', { name })" :title="$t('Configurer')" @click="emit('configure')">
          <PhGearSix :size="16" />
        </button>
        <button type="button" class="tool" :aria-label="$t('Masquer {name}', { name })" :title="$t('Masquer')" @click="store.setHidden(widget.id, true)">
          <PhEyeSlash :size="16" />
        </button>
        <button
          v-if="!confirmDelete"
          type="button"
          class="tool"
          :aria-label="$t('Supprimer {name}', { name })"
          :title="$t('Supprimer')"
          @click="confirmDelete = true"
        >
          <PhTrash :size="16" />
        </button>
        <button v-else type="button" class="tool danger" @click="store.removeWidget(widget.id)" @blur="confirmDelete = false">
          {{ $t('Supprimer ?') }}
        </button>
      </span>
    </div>
  </section>
</template>

<style scoped>
.frame {
  height: 100%;
  overflow: hidden;
  transition: box-shadow var(--dur) var(--ease), transform var(--dur) var(--ease);
}
.content {
  height: 100%;
  padding: 18px 20px;
}
.t-search {
  border-radius: var(--radius-pill);
}
.t-search .content {
  padding: 0;
}
.t-search:focus-within:not(.editing) {
  box-shadow: var(--focus-ring), var(--shadow-card);
}
.frame.editing {
  box-shadow: var(--shadow-float);
}
.frame.editing .content {
  opacity: 0.55;
  filter: saturate(0.85);
  transition: opacity var(--dur);
}
:global(.cell.active) .frame {
  transform: scale(1.015);
}
.edit-bar {
  position: absolute;
  inset: 8px 8px auto 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 4px 4px 4px 10px;
  border-radius: var(--radius-pill);
  background: rgb(var(--surface-rgb) / 0.94);
  border: 1px solid var(--surface-border);
  box-shadow: 0 4px 12px -6px rgb(0 0 0 / 0.2);
  z-index: 2;
}
.t-search .edit-bar {
  inset: 50% 10px auto auto;
  transform: translateY(-50%);
}
.handle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
}
.t-search .handle {
  display: none;
}
.actions {
  display: inline-flex;
  gap: 2px;
}
.tool {
  height: 30px;
  min-width: 30px;
  padding: 0 8px;
  border-radius: var(--radius-pill);
  border: none;
  background: transparent;
  display: inline-grid;
  place-items: center;
  color: var(--text-2);
  font-size: 12.5px;
  font-weight: 600;
}
.tool:hover {
  background: var(--accent-soft);
  color: var(--text-1);
}
.tool.danger {
  color: #fff;
  background: var(--down);
}
</style>
