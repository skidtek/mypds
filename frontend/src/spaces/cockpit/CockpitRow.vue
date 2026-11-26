<script setup lang="ts">
import { PhArrowDown, PhArrowUp, PhPlus, PhTrash } from '@phosphor-icons/vue'
import { ref } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import type { CockpitRow } from '@/api/types'
import { useCockpit } from '@/stores/cockpit'
import TileFrame from './TileFrame.vue'

const props = defineProps<{ row: CockpitRow; groupId: string; index: number; count: number }>()
const emit = defineEmits<{ addTile: []; configure: [tileId: string] }>()
const store = useCockpit()
const confirmDelete = ref(false)

function removeRow() {
  if (props.row.tiles.length && !confirmDelete.value) {
    confirmDelete.value = true
    return
  }
  store.removeRow(props.groupId, props.row.id)
}
</script>

<template>
  <section class="row" :class="{ editing: store.editing }" :aria-label="$t('Ligne {n}', { n: index + 1 })">
    <header v-if="store.editing" class="row-bar">
      <span class="faint">{{ $t('Ligne {n}', { n: index + 1 }) }}</span>
      <span class="tools">
        <button type="button" class="icon-btn" :aria-label="$t('Monter la ligne')" :disabled="index === 0" @click="store.moveRow(groupId, row.id, -1)"><PhArrowUp :size="15" /></button>
        <button type="button" class="icon-btn" :aria-label="$t('Descendre la ligne')" :disabled="index === count - 1" @click="store.moveRow(groupId, row.id, 1)"><PhArrowDown :size="15" /></button>
        <button type="button" class="btn small" @click="emit('addTile')"><PhPlus :size="14" /> {{ $t('Tuile') }}</button>
        <button type="button" class="icon-btn" :class="{ danger: confirmDelete }" :aria-label="confirmDelete ? $t('Confirmer : supprimer la ligne et ses tuiles') : $t('Supprimer la ligne')" @click="removeRow" @blur="confirmDelete = false"><PhTrash :size="15" /></button>
      </span>
    </header>
    <!-- Le groupe de glisser-déposer est propre à l'onglet : une tuile ne peut pas changer de groupe par accident -->
    <VueDraggable
      v-model="row.tiles"
      class="tiles"
      :group="`tiles-${groupId}`"
      :disabled="!store.editing"
      handle=".handle"
      :animation="220"
      ghost-class="ghost"
      @end="store.save()"
      @add="store.save()"
    >
      <div v-for="t in row.tiles" :key="t.id" class="cell" :data-tile-type="t.type" :style="{ '--w': t.width.desktop }">
        <TileFrame :tile="t" :group-id="groupId" @configure="emit('configure', t.id)" />
      </div>
    </VueDraggable>
    <button v-if="store.editing && !row.tiles.length" type="button" class="drop-hint" @click="emit('addTile')">
      <PhPlus :size="16" /> {{ $t('Ajouter une tuile ou glisser une tuile ici') }}
    </button>
  </section>
</template>

<style scoped>
.row {
  display: grid;
  gap: 10px;
}
.row.editing {
  padding: 10px;
  border-radius: var(--radius-card);
  border: 1.5px dashed color-mix(in srgb, var(--text-3) 60%, transparent);
}
.row-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12.5px;
  font-weight: 600;
  padding: 0 4px;
}
.tools {
  display: flex;
  align-items: center;
  gap: 4px;
}
.icon-btn {
  width: 30px;
  height: 30px;
}
.icon-btn:disabled {
  opacity: 0.35;
}
.icon-btn.danger {
  background: var(--down);
  color: #fff;
}
.tiles {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 18px;
  min-height: 0;
}
.editing .tiles {
  min-height: 60px;
}
.cell {
  grid-column: span var(--w);
  min-width: 0;
}
.ghost {
  opacity: 0.35;
}
.drop-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 60px;
  margin-top: -70px;
  border: none;
  border-radius: var(--radius-md);
  background: rgb(var(--surface-rgb) / 0.25);
  color: var(--text-2);
  font-weight: 560;
}
/* Tablette : grille de 6, les largeurs sont divisées par deux */
@media (max-width: 1023px) {
  .tiles {
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 14px;
  }
  .cell {
    grid-column: span min(6, max(2, calc((var(--w) + 1) / 2)));
  }
}
/* Mobile : les tuiles d'une ligne s'empilent, sans quitter leur ligne ni leur groupe */
@media (max-width: 699px) {
  .tiles {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .cell {
    grid-column: 1 / -1;
  }
}
</style>
