<script setup lang="ts">
import { PhCaretRight } from '@phosphor-icons/vue'

defineProps<{ title: string; subtitle?: string; actionLabel?: string }>()
const emit = defineEmits<{ action: [] }>()
</script>

<template>
  <header class="wh">
    <div class="wh-title">
      <span v-if="$slots.icon" class="wh-icon"><slot name="icon" /></span>
      <div>
        <h3>{{ title }}</h3>
        <p v-if="subtitle" class="muted">{{ subtitle }}</p>
      </div>
    </div>
    <slot name="right">
      <button v-if="actionLabel" type="button" class="icon-btn" :aria-label="actionLabel" @click="emit('action')">
        <PhCaretRight :size="16" weight="bold" />
      </button>
    </slot>
  </header>
</template>

<style scoped>
.wh {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.wh-title {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  min-width: 0;
}
.wh-icon {
  color: var(--text-1);
  display: grid;
  margin-top: 1px;
}
h3 {
  font-size: 17px;
  font-weight: 650;
}
p {
  margin: 2px 0 0;
  font-size: 13px;
}
.icon-btn {
  width: 30px;
  height: 30px;
  margin: -4px -6px 0 0;
}
</style>
