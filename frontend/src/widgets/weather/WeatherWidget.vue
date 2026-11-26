<script setup lang="ts">
import { PhArrowClockwise, PhCaretRight, PhDrop, PhMapPin, PhSunHorizon, PhWind } from '@phosphor-icons/vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '@/api/client'
import type { Widget, WeatherReport } from '@/api/types'
import { syncedLabel } from '@/design-system/time'
import { usePolling } from '@/design-system/usePolling'
import { usePreferences } from '@/stores/preferences'
import { AIR_LABELS, LEVEL_COLORS, rainExpected, sunProgress, UV_COLORS, UV_LABELS, uvLevel, windFrom, windValue } from './metrics'
import WeatherIcon from './WeatherIcon.vue'
import WeatherSky from './WeatherSky.vue'
import { intlLocale, t } from '@/i18n'

const props = defineProps<{ widget: Widget; editing: boolean }>()
const emit = defineEmits<{ configure: [] }>()
const prefs = usePreferences()
const report = ref<WeatherReport | null>(null)
const error = ref('')
const loading = ref(false)

const cfg = computed(() => props.widget.config as { label: string; latitude: number | null; longitude: number | null; forecast_days: number })
const configured = computed(() => cfg.value.latitude != null && cfg.value.longitude != null)

async function load() {
  if (!configured.value) return
  loading.value = true
  try {
    const q = new URLSearchParams({ lat: String(cfg.value.latitude), lon: String(cfg.value.longitude), unit: prefs.prefs.temperature_unit })
    report.value = await api<WeatherReport>(`/api/v1/weather?${q}`)
    error.value = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

const { refresh } = usePolling(load, 15 * 60 * 1000)
watch(() => [cfg.value.latitude, cfg.value.longitude, prefs.prefs.temperature_unit], () => void refresh())

const today = computed(() => report.value?.days[0])
const forecast = computed(() => report.value?.days.slice(1, 1 + (cfg.value.forecast_days ?? 5)) ?? [])
const dayName = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString(intlLocale.value, { weekday: 'short' }).replace('.', '')
const round = (n: number) => Math.round(n)
const num = (n: number, digits = 0) => n.toLocaleString(intlLocale.value, { maximumFractionDigits: digits })

// Position du soleil recalculée chaque minute (heure locale du lieu)
const now = ref(Date.now())
let clock: number | undefined
onMounted(() => (clock = window.setInterval(() => (now.value = Date.now()), 60_000)))
onBeforeUnmount(() => window.clearInterval(clock))
const sun = computed(() => (report.value ? sunProgress(report.value, now.value) : 0.5))

// Pluie attendue aujourd'hui → précipitations ; sinon → vent
const showRain = computed(() => !!report.value && rainExpected(report.value))
const rain = computed(() => {
  const d = today.value
  return { mm: d?.precipitation_sum ?? report.value?.current.precipitation ?? 0, pct: d?.precipitation_probability ?? null }
})
const wind = computed(() => {
  const c = report.value?.current
  if (!c || c.wind_speed == null) return null
  const u = report.value!.unit
  return {
    speed: windValue(c.wind_speed, u),
    gusts: c.wind_gusts != null && c.wind_gusts >= c.wind_speed + 10 ? windValue(c.wind_gusts, u).value : null,
    from: c.wind_direction != null ? t(windFrom(c.wind_direction)) : null,
    deg: c.wind_direction ?? 0,
  }
})
const air = computed(() => {
  const a = report.value?.air
  if (!a) return null
  const level = Math.min(5, Math.max(0, a.level))
  return {
    label: t(AIR_LABELS[a.scale][level]!),
    color: LEVEL_COLORS[level],
    title: t('Qualité de l\'air : {label} (indice {scale} {index})', {
      label: t(AIR_LABELS[a.scale][level]!),
      scale: a.scale === 'eu' ? t('européen') : t('américain'),
      index: Math.round(a.index),
    }),
  }
})
const uv = computed(() => {
  const v = today.value?.uv_index_max
  if (v == null) return null
  const l = uvLevel(v)
  return { value: Math.round(v), label: t(UV_LABELS[l]!), color: UV_COLORS[l] }
})
</script>

<template>
  <div class="weather">
    <template v-if="!configured">
      <div class="empty">
        <WeatherIcon condition="partly-cloudy" :size="48" />
        <p>{{ $t('Choisissez une ville pour afficher la météo.') }}</p>
        <button class="btn small" type="button" :disabled="editing" @click="emit('configure')">{{ $t('Choisir une ville') }}</button>
      </div>
    </template>
    <template v-else-if="report">
      <WeatherSky class="sky" :condition="report.current.condition" :sun="sun" :wind="report.current.wind_speed ?? 0" :paused="editing" />
      <div class="main">
        <WeatherIcon class="big-icon" :condition="report.current.condition" :day="report.current.is_day" :size="76" />
        <div class="now">
          <button class="place" type="button" :disabled="editing" :title="$t('{name} — configurer', { name: cfg.label })" @click="emit('configure')">
            <span>{{ cfg.label || $t('Ma ville') }}</span>
            <PhMapPin :size="14" />
            <PhCaretRight class="chev" :size="14" weight="bold" />
          </button>
          <p class="temp">
            {{ round(report.current.temperature) }}<span class="unit">°{{ report.unit === 'celsius' ? 'C' : 'F' }}</span>
          </p>
          <p class="label">{{ $t(report.current.label) }}</p>
        </div>
        <div v-if="today" class="side">
          <span class="minmax">{{ round(today.temp_max) }}° / {{ round(today.temp_min) }}°</span>
          <span class="sun-times">
            <span :title="$t('Lever du soleil')"><PhSunHorizon :size="15" weight="fill" class="rise" /> {{ today.sunrise }}</span>
            <span :title="$t('Coucher du soleil')"><PhSunHorizon :size="15" weight="fill" class="set" /> {{ today.sunset }}</span>
          </span>
        </div>
      </div>
      <ul class="metrics">
        <li v-if="showRain" :title="$t('Précipitations attendues aujourd\'hui')">
          <PhDrop :size="16" weight="fill" class="ic rain" />
          <span class="v">{{ $t('{mm} mm', { mm: num(rain.mm, 1) }) }}</span>
          <span v-if="rain.pct != null" class="s">{{ Math.round(rain.pct) }} %</span>
        </li>
        <li v-else-if="wind" :title="wind.from ? $t('Vent du {dir}', { dir: wind.from }) : $t('Vent')">
          <PhWind :size="16" class="ic" />
          <span class="v">{{ wind.speed.value }} {{ wind.speed.unit }}</span>
          <span v-if="wind.gusts" class="s">{{ $t('rafales {n}', { n: wind.gusts }) }}</span>
          <span v-else-if="wind.from" class="s arrow" :style="{ transform: `rotate(${wind.deg + 180}deg)` }" aria-hidden="true">↑</span>
        </li>
        <li v-if="air" :title="air.title">
          <i class="dot" :style="{ background: air.color }" />
          <span class="s">{{ $t('Air') }}</span>
          <span class="v">{{ air.label }}</span>
        </li>
        <li v-if="uv" :title="$t('Indice UV maximal du jour : {label}', { label: uv.label })">
          <i class="dot" :style="{ background: uv.color }" />
          <span class="s">UV</span>
          <span class="v">{{ uv.value }}</span>
        </li>
      </ul>
      <ol v-if="forecast.length" class="forecast" :aria-label="$t('Prévisions')">
        <li v-for="d in forecast" :key="d.date" :title="$t(d.label)">
          <span class="dn">{{ dayName(d.date) }}</span>
          <WeatherIcon :condition="d.condition" :size="26" />
          <span class="mx">{{ round(d.temp_max) }}°</span>
          <span class="mn faint">{{ round(d.temp_min) }}°</span>
        </li>
      </ol>
      <p class="sync faint" :title="report.attribution">{{ syncedLabel(report.fetched_at) }} · Open-Meteo</p>
    </template>
    <div v-else-if="error" class="empty">
      <p>{{ $t('Météo indisponible.') }}<br /><span class="faint">{{ error }}</span></p>
      <button class="btn small" type="button" @click="refresh()"><PhArrowClockwise :size="14" /> {{ $t('Réessayer') }}</button>
    </div>
    <div v-else class="skeleton" aria-busy="true" :aria-label="$t('Chargement de la météo')" />
  </div>
</template>

<style scoped>
.weather {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  container-type: size;
}
/* Le ciel remplit toute la tuile (au-delà de la marge intérieure du cadre) */
.sky {
  inset: -18px -20px;
}
.weather > :not(.sky) {
  position: relative;
  z-index: 1;
}
.side {
  margin-left: auto;
  align-self: flex-start;
  display: grid;
  justify-items: end;
  gap: 6px;
  padding-top: 2px;
  font-size: 13.5px;
  font-weight: 560;
}
.sun-times {
  display: flex;
  gap: 12px;
  color: var(--text-2);
}
.sun-times span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.metrics {
  list-style: none;
  margin: auto 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.metrics li {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 11px;
  border-radius: var(--radius-pill);
  background: rgb(var(--surface-rgb) / 0.42);
  border: 1px solid var(--hairline);
  font-size: 13px;
  white-space: nowrap;
}
.metrics .v {
  font-weight: 640;
}
.metrics .s {
  color: var(--text-2);
}
.metrics .ic {
  color: var(--text-2);
}
.metrics .ic.rain {
  color: #3a9bff;
}
.metrics .arrow {
  display: inline-block;
  font-weight: 700;
}
.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgb(var(--surface-rgb) / 0.6);
}
.main {
  display: flex;
  align-items: center;
  gap: 18px;
  padding-left: 4px;
}
.now {
  min-width: 0;
}
.place {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: none;
  background: none;
  padding: 0;
  font-weight: 600;
  font-size: 15px;
  color: var(--text-1);
}
.place .chev {
  color: var(--text-3);
}
.temp {
  margin: 2px 0 0;
  font-family: var(--font-display);
  font-size: 46px;
  line-height: 1;
  font-weight: 640;
  letter-spacing: -0.03em;
}
.unit {
  font-size: 26px;
  vertical-align: top;
  margin-left: 4px;
  letter-spacing: 0;
}
.label {
  margin: 6px 0 0;
  color: var(--text-2);
  font-size: 15px;
}
.rise {
  color: #ffb02e;
}
.set {
  color: #ff8a3d;
}
.minmax {
  color: var(--text-1);
  font-size: 15px;
}
.forecast {
  display: none;
  list-style: none;
  margin: 0;
  padding: 10px 0 0;
  border-top: 1px solid var(--hairline);
  justify-content: space-between;
  gap: 6px;
}
.forecast li {
  display: grid;
  justify-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 560;
}
.dn {
  text-transform: capitalize;
  color: var(--text-2);
}
.sync {
  display: none;
  margin: 0;
  font-size: 11.5px;
}
.empty {
  height: 100%;
  display: grid;
  place-content: center;
  justify-items: center;
  text-align: center;
  gap: 10px;
  color: var(--text-2);
  font-size: 14px;
}
.empty p {
  margin: 0;
}
.skeleton {
  flex: 1;
  border-radius: var(--radius-md);
  background: linear-gradient(100deg, transparent 30%, rgb(255 255 255 / 0.25) 50%, transparent 70%) 0 0 / 200% 100%;
  animation: shimmer 1.4s infinite linear;
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}
@container (max-width: 330px) {
  .sun-times {
    display: none;
  }
}
@container (min-height: 250px) {
  .forecast {
    display: flex;
  }
  .metrics {
    margin-top: 0;
  }
  .sync {
    display: block;
    margin-top: auto;
  }
}
@container (max-height: 150px) {
  .metrics {
    display: none;
  }
  .big-icon {
    width: 56px !important;
  }
}
</style>
