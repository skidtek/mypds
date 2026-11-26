<script setup lang="ts">
import { PhArrowUpRight } from '@phosphor-icons/vue'
import { computed } from 'vue'
import type { CockpitTile } from '@/api/types'
import TileIcon from '../TileIcon.vue'

const props = defineProps<{ tile: CockpitTile; editing: boolean }>()
const host = computed(() => {
  try {
    return new URL(props.tile.config.url ?? '').host
  } catch {
    return ''
  }
})
</script>

<template>
  <component
    :is="editing ? 'div' : 'a'"
    class="lnk"
    :href="editing ? undefined : tile.config.url"
    target="_blank"
    rel="noopener noreferrer"
    :aria-label="$t('{name}, ouvrir', { name: tile.config.label })"
  >
    <TileIcon :icon="tile.config.icon" fallback="link" :size="44" />
    <div class="info">
      <strong>{{ tile.config.label }}</strong>
      <span class="faint">{{ host }}</span>
    </div>
    <PhArrowUpRight class="go" :size="15" />
  </component>
</template>

<style scoped>
.lnk {
  position: relative;
  height: 100%;
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}
.info {
  display: grid;
  gap: 2px;
  min-width: 0;
}
strong {
  font-size: 15.5px;
  font-weight: 650;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.faint {
  font-size: 12.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.go {
  position: absolute;
  right: -6px;
  bottom: -6px;
  color: var(--text-3);
  opacity: 0;
  transition: opacity var(--dur-fast);
}
.lnk:hover .go {
  opacity: 1;
}
</style>
