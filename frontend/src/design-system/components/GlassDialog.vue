<script setup lang="ts">
import { PhX } from '@phosphor-icons/vue'
import { onMounted, ref } from 'vue'

defineProps<{ title: string; wide?: boolean }>()
const emit = defineEmits<{ close: [] }>()
const dialog = ref<HTMLDialogElement>()

onMounted(() => dialog.value?.showModal())

function onClick(e: MouseEvent) {
  if (e.target === dialog.value) emit('close')
}
</script>

<template>
  <dialog ref="dialog" class="dlg" :class="{ wide }" :aria-label="title" @cancel.prevent="emit('close')" @click="onClick">
    <div class="dlg-panel glass glass-strong">
      <header class="dlg-head">
        <h2>{{ title }}</h2>
        <button class="icon-btn" type="button" :aria-label="$t('Fermer')" @click="emit('close')"><PhX :size="18" /></button>
      </header>
      <div class="dlg-body"><slot /></div>
      <footer v-if="$slots.footer" class="dlg-foot"><slot name="footer" /></footer>
    </div>
  </dialog>
</template>

<style scoped>
.dlg {
  padding: 0;
  border: none;
  background: transparent;
  max-width: min(520px, calc(100vw - 24px));
  width: 100%;
  color: var(--text-1);
}
.dlg.wide {
  max-width: min(760px, calc(100vw - 24px));
}
.dlg::backdrop {
  background: rgb(15 20 40 / 0.28);
  backdrop-filter: blur(6px);
}
.dlg[open] {
  animation: pop var(--dur) var(--ease);
}
@keyframes pop {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.98);
  }
}
.dlg-panel {
  padding: 22px 24px 20px;
  max-height: calc(100dvh - 48px);
  overflow: auto;
}
.dlg-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.dlg-head h2 {
  font-size: 19px;
  font-weight: 650;
}
.dlg-body {
  display: grid;
  gap: 16px;
}
.dlg-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
</style>
