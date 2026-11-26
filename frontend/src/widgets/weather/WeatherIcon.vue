<script setup lang="ts">
import { PhCloud, PhCloudFog, PhCloudLightning, PhCloudRain, PhCloudSnow, PhMoon, PhQuestion, PhSun } from '@phosphor-icons/vue'
import type { Condition } from '@/api/types'

withDefaults(defineProps<{ condition: Condition; day?: boolean; size?: number }>(), { day: true, size: 56 })
</script>

<template>
  <span class="wi" :style="{ width: `${size}px`, height: `${size}px` }" role="img" aria-hidden="true">
    <template v-if="condition === 'clear'">
      <PhSun v-if="day" class="sun" :size="size" weight="fill" />
      <PhMoon v-else class="moon" :size="size * 0.85" weight="fill" />
    </template>
    <template v-else-if="condition === 'partly-cloudy'">
      <PhSun v-if="day" class="sun behind" :size="size * 0.72" weight="fill" />
      <PhMoon v-else class="moon behind" :size="size * 0.6" weight="fill" />
      <PhCloud class="cloud front" :size="size * 0.82" weight="fill" />
    </template>
    <PhCloud v-else-if="condition === 'cloudy'" class="cloud" :size="size" weight="fill" />
    <PhCloudFog v-else-if="condition === 'fog'" class="fog" :size="size" weight="fill" />
    <PhCloudRain v-else-if="['rain', 'drizzle', 'showers'].includes(condition)" class="rain" :size="size" weight="fill" />
    <PhCloudSnow v-else-if="condition === 'snow'" class="snow" :size="size" weight="fill" />
    <PhCloudLightning v-else-if="condition === 'thunderstorm'" class="storm" :size="size" weight="fill" />
    <PhQuestion v-else class="fog" :size="size * 0.7" />
  </span>
</template>

<style scoped>
.wi {
  position: relative;
  display: inline-grid;
  place-items: center;
  flex: none;
}
.wi > * {
  filter: drop-shadow(0 4px 8px rgb(30 40 80 / 0.18));
}
.sun {
  color: #ffc62e;
}
.moon {
  color: #e9e4ff;
}
.cloud {
  color: #fff;
}
:global([data-mode='dark']) .cloud {
  color: #e6e9f5;
}
.behind {
  position: absolute;
  top: 2%;
  left: 2%;
}
.front {
  position: absolute;
  right: 0;
  bottom: 4%;
}
.fog {
  color: #dfe4f0;
}
.rain {
  color: #8fb3ef;
}
.snow {
  color: #d6e4fb;
}
.storm {
  color: #a598f2;
}
</style>
