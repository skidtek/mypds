<script setup lang="ts">
import { PhCalendarBlank, PhCheckSquare, PhCloudSun, PhMagnifyingGlass, PhNote, PhRss } from '@phosphor-icons/vue'
import type { WidgetType } from '@/api/types'
import GlassDialog from '@/design-system/components/GlassDialog.vue'
import { tk } from '@/i18n'

const emit = defineEmits<{ close: []; add: [type: WidgetType] }>()
const CATALOG = [
  { type: 'search', icon: PhMagnifyingGlass, name: tk('Recherche web'), desc: tk('Google, Bing, DuckDuckGo, Qwant ou votre moteur.') },
  { type: 'weather', icon: PhCloudSun, name: tk('Météo'), desc: tk('Conditions actuelles et prévisions pour une ville.') },
  { type: 'calendar', icon: PhCalendarBlank, name: tk('Agenda'), desc: tk('Vos prochains rendez-vous (flux ICS).') },
  { type: 'news', icon: PhRss, name: tk('News'), desc: tk('Derniers articles de vos flux RSS / Atom.') },
  { type: 'todo', icon: PhCheckSquare, name: tk('Tâches'), desc: tk('Liste de choses à faire ; les tâches terminées restent consultables avec leurs dates.') },
  { type: 'note', icon: PhNote, name: tk('Post-it'), desc: tk('Notes à onglets, avec couleur et texture au choix.') },
] as const
</script>

<template>
  <GlassDialog :title="$t('Ajouter un widget')" @close="emit('close')">
    <ul class="lib">
      <li v-for="c in CATALOG" :key="c.type">
        <button type="button" @click="emit('add', c.type)">
          <span class="ic"><component :is="c.icon" :size="24" /></span>
          <span>
            <strong>{{ $t(c.name) }}</strong>
            <span class="muted">{{ $t(c.desc) }}</span>
          </span>
        </button>
      </li>
    </ul>
  </GlassDialog>
</template>

<style scoped>
.lib {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.lib button {
  width: 100%;
  display: flex;
  gap: 14px;
  align-items: center;
  text-align: left;
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--hairline);
  background: rgb(var(--surface-rgb) / 0.55);
  transition: background var(--dur-fast), transform var(--dur-fast);
}
.lib button:hover {
  background: rgb(var(--surface-rgb) / 0.9);
  transform: translateY(-1px);
}
.lib button > span:last-child {
  display: grid;
  gap: 2px;
  font-size: 13.5px;
}
.lib strong {
  font-size: 15px;
}
.ic {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: #fff;
  background: linear-gradient(135deg, #5ac8fa, #7d6cf2);
  flex: none;
}
</style>
