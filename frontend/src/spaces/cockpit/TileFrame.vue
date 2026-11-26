<script setup lang="ts">
import { PhArrowsLeftRight, PhDotsSixVertical, PhGearSix, PhMinus, PhPlus, PhTrash } from '@phosphor-icons/vue'
import { computed, ref } from 'vue'
import type { CockpitTile } from '@/api/types'
import { useCockpit } from '@/stores/cockpit'
import ActivityTile from './tiles/ActivityTile.vue'
import AlertsTile from './tiles/AlertsTile.vue'
import LinkTile from './tiles/LinkTile.vue'
import ProxmoxGuestTile from './tiles/ProxmoxGuestTile.vue'
import ProxmoxNodeTile from './tiles/ProxmoxNodeTile.vue'
import ProxmoxSummaryTile from './tiles/ProxmoxSummaryTile.vue'
import DockerContainerTile from './tiles/DockerContainerTile.vue'
import DockerSummaryTile from './tiles/DockerSummaryTile.vue'
import SynologySummaryTile from './tiles/SynologySummaryTile.vue'
import UnifiDeviceTile from './tiles/UnifiDeviceTile.vue'
import UnifiSummaryTile from './tiles/UnifiSummaryTile.vue'

const props = defineProps<{ tile: CockpitTile; groupId: string }>()
const emit = defineEmits<{ configure: [] }>()
const store = useCockpit()
const confirmDelete = ref(false)
const moveOpen = ref(false)
const otherGroups = computed(() => store.doc?.groups.filter((g) => g.id !== props.groupId) ?? [])
const compact = computed(() => ['proxmox.guest', 'unifi.device', 'docker.container', 'link'].includes(props.tile.type))

function width(delta: number) {
  const w = Math.max(1, Math.min(12, props.tile.width.desktop + delta))
  store.updateTile(props.tile.id, { width: { desktop: w } })
}
</script>

<template>
  <article class="tile glass" :class="{ compact, editing: store.editing }">
    <div class="content" :inert="store.editing || undefined">
      <ProxmoxSummaryTile v-if="tile.type === 'proxmox.summary'" :tile="tile" />
      <ProxmoxNodeTile v-else-if="tile.type === 'proxmox.node'" :tile="tile" />
      <ProxmoxGuestTile v-else-if="tile.type === 'proxmox.guest'" :tile="tile" :editing="store.editing" />
      <UnifiSummaryTile v-else-if="tile.type === 'unifi.summary'" :tile="tile" />
      <UnifiDeviceTile v-else-if="tile.type === 'unifi.device'" :tile="tile" />
      <SynologySummaryTile v-else-if="tile.type === 'synology.summary'" :tile="tile" :editing="store.editing" />
      <DockerSummaryTile v-else-if="tile.type === 'docker.summary'" :tile="tile" />
      <DockerContainerTile v-else-if="tile.type === 'docker.container'" :tile="tile" :editing="store.editing" />
      <AlertsTile v-else-if="tile.type === 'alerts'" :editing="store.editing" />
      <ActivityTile v-else-if="tile.type === 'activity'" :editing="store.editing" />
      <LinkTile v-else :tile="tile" :editing="store.editing" />
    </div>
    <div v-if="store.editing" class="bar" role="toolbar" :aria-label="$t('Actions de la tuile')">
      <span class="handle" :title="$t('Glisser pour déplacer dans le groupe')" aria-hidden="true"><PhDotsSixVertical :size="16" weight="bold" /></span>
      <span class="w">
        <button type="button" class="tool" :aria-label="$t('Réduire la largeur')" :disabled="tile.width.desktop <= 1" @click="width(-1)"><PhMinus :size="13" /></button>
        <span class="wv" :aria-label="$t('Largeur {n} sur 12', { n: tile.width.desktop })">{{ tile.width.desktop }}/12</span>
        <button type="button" class="tool" :aria-label="$t('Augmenter la largeur')" :disabled="tile.width.desktop >= 12" @click="width(1)"><PhPlus :size="13" /></button>
      </span>
      <span class="actions">
        <button type="button" class="tool" :aria-label="$t('Configurer la tuile')" :title="$t('Configurer')" @click="emit('configure')"><PhGearSix :size="15" /></button>
        <span v-if="otherGroups.length" class="move">
          <button type="button" class="tool" :aria-label="$t('Déplacer vers un autre onglet')" :title="$t('Déplacer vers un autre onglet')" :aria-expanded="moveOpen" @click="moveOpen = !moveOpen">
            <PhArrowsLeftRight :size="15" />
          </button>
          <ul v-if="moveOpen" class="menu glass glass-strong">
            <li v-for="g in otherGroups" :key="g.id">
              <button type="button" @click="store.moveTileToGroup(tile.id, g.id); moveOpen = false">{{ g.title }}</button>
            </li>
          </ul>
        </span>
        <button v-if="!confirmDelete" type="button" class="tool" :aria-label="$t('Supprimer la tuile')" :title="$t('Supprimer')" @click="confirmDelete = true"><PhTrash :size="15" /></button>
        <button v-else type="button" class="tool danger" @click="store.removeTile(tile.id)" @blur="confirmDelete = false">{{ $t('Supprimer ?') }}</button>
      </span>
    </div>
  </article>
</template>

<style scoped>
.tile {
  position: relative;
  height: 100%;
  padding: 18px 20px;
  transition: transform var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
.tile.compact {
  padding: 16px 18px;
}
.tile:not(.editing):has(a:hover) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-float);
}
.content {
  height: 100%;
}
.editing .content {
  opacity: 0.6;
  padding-top: 30px;
}
.bar {
  position: absolute;
  inset: 6px 6px auto 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 3px;
  border-radius: var(--radius-pill);
  background: rgb(var(--surface-rgb) / 0.94);
  border: 1px solid var(--surface-border);
  z-index: 3;
}
.handle {
  cursor: grab;
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  color: var(--text-2);
  touch-action: none;
}
.w,
.actions {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.wv {
  font-size: 11.5px;
  font-weight: 650;
  min-width: 34px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.tool {
  height: 26px;
  min-width: 26px;
  padding: 0 6px;
  border: none;
  border-radius: var(--radius-pill);
  background: transparent;
  display: inline-grid;
  place-items: center;
  color: var(--text-2);
  font-size: 12px;
  font-weight: 600;
}
.tool:hover:not(:disabled) {
  background: var(--accent-soft);
  color: var(--text-1);
}
.tool:disabled {
  opacity: 0.35;
}
.tool.danger {
  background: var(--down);
  color: #fff;
}
.move {
  position: relative;
}
.menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  list-style: none;
  margin: 0;
  padding: 6px;
  min-width: 170px;
  border-radius: var(--radius-sm);
  z-index: 10;
}
.menu button {
  width: 100%;
  text-align: left;
  border: none;
  background: none;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 13.5px;
}
.menu button:hover {
  background: var(--accent-soft);
}
</style>
