<script setup lang="ts">
/**
 * Ciel animé derrière la tuile météo : moment de la journée (aube, jour, crépuscule, nuit) et temps
 * qu'il fait (nuages, pluie, neige, orage, brouillard, vent). Dessin original en CSS, sans image.
 * Discret pour garder le texte lisible ; immobile si l'utilisateur réduit les animations.
 */
import { computed } from 'vue'
import type { Condition } from '@/api/types'

const props = defineProps<{
  condition: Condition
  /** Position du soleil : 0 = lever, 1 = coucher ; < 0 ou > 1 = nuit. */
  sun: number
  /** Vent en km/h (inclinaison de la pluie, vitesse des nuages, rafales visibles). */
  wind: number
  paused?: boolean
}>()

type Phase = 'night' | 'dawn' | 'day' | 'dusk'
const TWILIGHT = 0.07 // ~ 40 min sur une journée d'hiver
const phase = computed<Phase>(() => {
  const s = props.sun
  if (s < -TWILIGHT || s > 1 + TWILIGHT) return 'night'
  if (s < TWILIGHT) return 'dawn'
  if (s > 1 - TWILIGHT) return 'dusk'
  return 'day'
})

const c = computed(() => props.condition)
const wet = computed(() => ['rain', 'drizzle', 'showers', 'thunderstorm'].includes(c.value))
const cloudCount = computed(() =>
  c.value === 'clear' ? 0 : c.value === 'partly-cloudy' ? 2 : ['fog', 'unknown'].includes(c.value) ? 0 : 3,
)
const showSun = computed(() => phase.value !== 'night' && ['clear', 'partly-cloudy'].includes(c.value))
const showMoon = computed(() => phase.value === 'night' && ['clear', 'partly-cloudy'].includes(c.value))
const windy = computed(() => props.wind >= 30 && !wet.value && c.value !== 'snow')

/** Le soleil suit un arc : bas aux extrémités de la journée, haut à midi. */
const sunStyle = computed(() => {
  const p = Math.min(1.05, Math.max(-0.05, props.sun))
  const x = 6 + p * 88 // % de la largeur
  const y = 95 - Math.sin(Math.PI * Math.min(1, Math.max(0, p))) * 80 // % de la hauteur
  return { left: `${x}%`, top: `${y}%` }
})

// Gouttes, flocons, étoiles : positions pseudo-aléatoires mais stables (pas de saut à chaque rendu)
const rand = (i: number, k: number) => {
  const v = Math.sin(i * 12.9898 + k * 78.233) * 43758.5453
  return v - Math.floor(v)
}
const drops = computed(() =>
  Array.from({ length: c.value === 'drizzle' ? 26 : c.value === 'thunderstorm' || c.value === 'showers' ? 46 : 36 }, (_, i) => ({
    left: `${rand(i, 1) * 110 - 5}%`,
    delay: `${(-rand(i, 2) * 1.2).toFixed(2)}s`,
    dur: `${(0.55 + rand(i, 3) * 0.35).toFixed(2)}s`,
    len: `${10 + rand(i, 4) * 12}px`,
  })),
)
const flakes = computed(() =>
  Array.from({ length: 30 }, (_, i) => ({
    left: `${rand(i, 5) * 100}%`,
    delay: `${(-rand(i, 6) * 6).toFixed(2)}s`,
    dur: `${(4 + rand(i, 7) * 4).toFixed(2)}s`,
    size: `${2 + rand(i, 8) * 3}px`,
  })),
)
const stars = computed(() =>
  Array.from({ length: 22 }, (_, i) => ({
    left: `${rand(i, 9) * 100}%`,
    top: `${rand(i, 10) * 70}%`,
    delay: `${(-rand(i, 11) * 4).toFixed(2)}s`,
    size: `${1 + rand(i, 12) * 1.6}px`,
  })),
)
const gusts = Array.from({ length: 5 }, (_, i) => ({ top: `${18 + i * 15}%`, delay: `${-(i * 0.9).toFixed(1)}s`, w: `${30 + rand(i, 13) * 30}%` }))
// Inclinaison de la pluie et vitesse des nuages selon le vent
const tilt = computed(() => `${Math.min(28, props.wind * 0.45)}deg`)
const dx = computed(() => `${-Math.round(Math.tan((Math.min(28, props.wind * 0.45) * Math.PI) / 180) * 160)}px`)
const cloudSpeed = computed(() => `${Math.max(28, 90 - props.wind * 1.4)}s`)
</script>

<template>
  <div
    class="sky"
    :class="[`ph-${phase}`, `c-${condition}`, { paused, wet }]"
    :style="{ '--tilt': tilt, '--dx': dx, '--cloud-speed': cloudSpeed }"
    aria-hidden="true"
  >
    <div class="tint" />
    <template v-if="phase === 'night' && !['rain', 'drizzle', 'showers', 'thunderstorm', 'snow', 'fog', 'cloudy'].includes(condition)">
      <i v-for="(s, i) in stars" :key="`s${i}`" class="star" :style="{ left: s.left, top: s.top, width: s.size, height: s.size, animationDelay: s.delay }" />
    </template>
    <div v-if="showSun" class="sun" :style="sunStyle"><span class="rays" /></div>
    <div v-if="showMoon" class="moon" />
    <i v-for="n in cloudCount" :key="`c${n}`" class="cloud" :class="`k${n}`" />
    <div v-if="condition === 'fog'" class="fog"><i /><i /><i /></div>
    <template v-if="wet">
      <i v-for="(d, i) in drops" :key="`d${i}`" class="drop" :style="{ left: d.left, height: d.len, animationDelay: d.delay, animationDuration: d.dur }" />
    </template>
    <template v-if="condition === 'snow'">
      <i v-for="(f, i) in flakes" :key="`f${i}`" class="flake" :style="{ left: f.left, width: f.size, height: f.size, animationDelay: f.delay, animationDuration: f.dur }" />
    </template>
    <div v-if="condition === 'thunderstorm'" class="flash" />
    <template v-if="windy">
      <i v-for="(g, i) in gusts" :key="`g${i}`" class="gust" :style="{ top: g.top, width: g.w, animationDelay: g.delay }" />
    </template>
  </div>
</template>

<style scoped>
.sky {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
  border-radius: inherit;
}
/* Teinte du ciel : légère, le verre de la tuile reste dominant pour la lisibilité */
.tint {
  position: absolute;
  inset: 0;
  opacity: 0.55;
  transition: background 1.5s ease;
}
.ph-day .tint {
  background: linear-gradient(180deg, rgb(86 160 255 / 0.55), rgb(150 200 255 / 0.15));
}
.ph-dawn .tint {
  background: linear-gradient(180deg, rgb(120 130 220 / 0.4), rgb(255 160 120 / 0.45) 75%, rgb(255 200 120 / 0.5));
}
.ph-dusk .tint {
  background: linear-gradient(180deg, rgb(90 80 170 / 0.45), rgb(255 120 100 / 0.45) 70%, rgb(255 170 90 / 0.5));
}
.ph-night .tint {
  background: linear-gradient(180deg, rgb(15 22 60 / 0.75), rgb(40 50 110 / 0.35));
}
.c-cloudy .tint,
.c-fog .tint,
.wet .tint,
.c-snow .tint {
  filter: grayscale(0.65) brightness(0.92);
}
.c-thunderstorm .tint {
  filter: grayscale(0.7) brightness(0.7);
}

/* Soleil */
/* Soleil : un halo de lumière (l'icône de la tuile reste le symbole du temps) */
.sun {
  position: absolute;
  width: 150px;
  height: 150px;
  margin: -75px 0 0 -75px;
  border-radius: 50%;
  background: radial-gradient(circle, rgb(255 236 170 / 0.55) 0 8%, rgb(255 205 80 / 0.28) 22%, rgb(255 190 40 / 0) 62%);
  animation: glow 6s ease-in-out infinite;
  transition: left 60s linear, top 60s linear;
}
.ph-dawn .sun,
.ph-dusk .sun {
  width: 220px;
  height: 220px;
  margin: -110px 0 0 -110px;
  background: radial-gradient(circle, rgb(255 225 180 / 0.6) 0 7%, rgb(255 150 70 / 0.35) 24%, rgb(255 110 60 / 0) 62%);
}
.rays {
  position: absolute;
  inset: 18%;
  border-radius: 50%;
  background: repeating-conic-gradient(rgb(255 225 140 / 0.16) 0 5deg, transparent 5deg 24deg);
  mask: radial-gradient(circle, transparent 18%, #000 26%, transparent 70%);
  animation: spin 60s linear infinite;
}
.moon {
  position: absolute;
  left: 52%;
  top: 12%;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #fffef4, #d9dcef 70%);
  box-shadow: 0 0 24px 6px rgb(220 225 255 / 0.35);
}
.star {
  position: absolute;
  border-radius: 50%;
  background: #fff;
  animation: twinkle 4s ease-in-out infinite;
}

/* Nuages : formes floues qui dérivent (vitesse selon le vent) */
.cloud {
  position: absolute;
  height: 38%;
  border-radius: 999px;
  background: radial-gradient(ellipse at 50% 60%, rgb(255 255 255 / 0.7), rgb(255 255 255 / 0) 70%);
  filter: blur(6px);
  animation: drift var(--cloud-speed) linear infinite;
}
.ph-night .cloud {
  background: radial-gradient(ellipse at 50% 60%, rgb(170 180 220 / 0.45), rgb(170 180 220 / 0) 70%);
}
.wet .cloud,
.c-cloudy .cloud,
.c-snow .cloud {
  background: radial-gradient(ellipse at 50% 60%, rgb(200 205 220 / 0.75), rgb(200 205 220 / 0) 70%);
}
.c-thunderstorm .cloud {
  background: radial-gradient(ellipse at 50% 60%, rgb(110 115 140 / 0.8), rgb(110 115 140 / 0) 70%);
}
.cloud.k1 {
  top: -6%;
  width: 70%;
  animation-delay: calc(var(--cloud-speed) * -0.2);
}
.cloud.k2 {
  top: 18%;
  width: 55%;
  animation-delay: calc(var(--cloud-speed) * -0.65);
  animation-duration: calc(var(--cloud-speed) * 1.3);
}
.cloud.k3 {
  top: -14%;
  width: 90%;
  animation-delay: calc(var(--cloud-speed) * -0.45);
  animation-duration: calc(var(--cloud-speed) * 0.8);
}

/* Pluie : traits inclinés selon le vent */
.drop {
  position: absolute;
  top: -20%;
  width: 1.5px;
  border-radius: 2px;
  background: linear-gradient(to bottom, rgb(200 225 255 / 0), rgb(200 225 255 / 0.85));
  transform: rotate(var(--tilt));
  animation: fall 0.8s linear infinite;
}
.flake {
  position: absolute;
  top: -8%;
  border-radius: 50%;
  background: rgb(255 255 255 / 0.9);
  animation: snow 6s linear infinite;
}
.flash {
  position: absolute;
  inset: 0;
  background: rgb(255 255 255 / 0.9);
  opacity: 0;
  animation: flash 7s infinite;
}
.fog i {
  position: absolute;
  left: -30%;
  width: 160%;
  height: 22%;
  border-radius: 999px;
  background: rgb(230 232 240 / 0.45);
  filter: blur(10px);
  animation: fog 18s ease-in-out infinite alternate;
}
.fog i:nth-child(1) {
  top: 18%;
}
.fog i:nth-child(2) {
  top: 46%;
  animation-delay: -6s;
}
.fog i:nth-child(3) {
  top: 72%;
  animation-delay: -12s;
}
.gust {
  position: absolute;
  left: -40%;
  height: 1.5px;
  border-radius: 2px;
  background: linear-gradient(90deg, rgb(255 255 255 / 0), rgb(255 255 255 / 0.6), rgb(255 255 255 / 0));
  animation: gust 3.2s ease-in infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@keyframes glow {
  0%,
  100% {
    opacity: 0.85;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.06);
  }
}
@keyframes twinkle {
  0%,
  100% {
    opacity: 0.25;
  }
  50% {
    opacity: 1;
  }
}
@keyframes drift {
  from {
    transform: translateX(-80%);
  }
  to {
    transform: translateX(160%);
  }
}
@keyframes fall {
  from {
    transform: translate(0, 0) rotate(var(--tilt));
  }
  to {
    transform: translate(var(--dx), 160px) rotate(var(--tilt));
  }
}
@keyframes snow {
  0% {
    transform: translate(0, 0);
  }
  50% {
    transform: translate(10px, 110px);
  }
  100% {
    transform: translate(-4px, 230px);
  }
}
@keyframes flash {
  0%,
  89%,
  93%,
  100% {
    opacity: 0;
  }
  90%,
  92% {
    opacity: 0.35;
  }
  91% {
    opacity: 0.1;
  }
}
@keyframes fog {
  to {
    transform: translateX(18%);
  }
}
@keyframes gust {
  0% {
    transform: translateX(0);
    opacity: 0;
  }
  20% {
    opacity: 1;
  }
  100% {
    transform: translateX(260%);
    opacity: 0;
  }
}

.paused *,
.paused {
  animation-play-state: paused !important;
}
@media (prefers-reduced-motion: reduce) {
  .sky *,
  .sky {
    animation: none !important;
    transition: none !important;
  }
}
</style>
