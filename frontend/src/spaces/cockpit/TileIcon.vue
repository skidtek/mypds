<script setup lang="ts">
import { PhCube, PhDesktopTower, PhGlobe, PhHardDrives } from '@phosphor-icons/vue'
import { ref, watchEffect } from 'vue'
import type { IconRef } from '@/api/types'
import { iconColor } from './icons'

const props = withDefaults(defineProps<{ icon?: IconRef | null; fallback?: 'lxc' | 'qemu' | 'node' | 'link'; size?: number }>(), {
  fallback: 'link',
  size: 40,
})
const color = ref<string | null>(null)
watchEffect(async () => {
  color.value = props.icon?.kind === 'simple' ? await iconColor(props.icon.value) : null
})
</script>

<template>
  <span class="ti" :style="{ width: `${size}px`, height: `${size}px` }" aria-hidden="true">
    <span
      v-if="icon?.kind === 'simple'"
      class="mask"
      :style="{ maskImage: `url(/icons/simple/${icon.value}.svg)`, WebkitMaskImage: `url(/icons/simple/${icon.value}.svg)`, background: color ?? 'var(--text-1)' }"
    />
    <img v-else-if="icon?.kind === 'upload'" :src="`/api/v1/cockpit/icons/${icon.value}`" alt="" />
    <PhCube v-else-if="fallback === 'lxc'" :size="size * 0.55" weight="duotone" />
    <PhDesktopTower v-else-if="fallback === 'qemu'" :size="size * 0.55" weight="duotone" />
    <PhHardDrives v-else-if="fallback === 'node'" :size="size * 0.55" weight="duotone" />
    <PhGlobe v-else :size="size * 0.55" weight="duotone" />
  </span>
</template>

<style scoped>
.ti {
  display: inline-grid;
  place-items: center;
  flex: none;
  border-radius: 28%;
  background: rgb(var(--surface-rgb) / 0.75);
  border: 1px solid var(--surface-border);
  box-shadow: 0 4px 12px -6px rgb(0 0 0 / 0.25);
  color: var(--accent);
  overflow: hidden;
}
.mask {
  width: 58%;
  height: 58%;
  mask-size: contain;
  mask-repeat: no-repeat;
  mask-position: center;
  -webkit-mask-size: contain;
  -webkit-mask-repeat: no-repeat;
  -webkit-mask-position: center;
}
img {
  width: 76%;
  height: 76%;
  object-fit: contain;
}
</style>
