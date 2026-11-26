<script setup lang="ts">
import { computed } from 'vue'
import { DEFAULT_BRANDING, logoUrl, usePreferences } from '@/stores/preferences'
import { t } from '@/i18n'

defineProps<{ compact?: boolean }>()
const store = usePreferences()
const b = computed(() => store.branding)
const title = computed(() => (b.value.display === 'short' ? b.value.short_title : b.value.title))
const side = computed(() => b.value.show_logo && b.value.display !== 'hidden' && (b.value.logo_position === 'left' || b.value.logo_position === 'right'))
const subtitle = computed(() => (b.value.subtitle === DEFAULT_BRANDING.subtitle ? t(DEFAULT_BRANDING.subtitle) : b.value.subtitle))
</script>

<template>
  <header v-if="b.display !== 'hidden' || b.show_logo" class="brand" :class="{ compact }">
    <img v-if="b.show_logo && !side" class="logo" :class="{ custom: !!b.logo_version }" :src="logoUrl(b)" alt="" width="56" height="56" />
    <template v-if="b.display !== 'hidden'">
      <!-- Logo à gauche ou à droite : sur la ligne du titre -->
      <div v-if="side" class="title-row" :class="b.logo_position">
        <img class="logo side" :class="{ custom: !!b.logo_version }" :src="logoUrl(b)" alt="" width="52" height="52" />
        <h1>{{ title }}</h1>
      </div>
      <h1 v-else>{{ title }}</h1>
      <p v-if="b.subtitle" class="subtitle"><span>{{ subtitle }}</span></p>
    </template>
  </header>
</template>

<style scoped>
.brand {
  display: grid;
  justify-items: center;
  gap: 6px;
  text-align: center;
  padding: 0 16px 20px;
}
.logo {
  width: 56px;
  height: 56px;
  filter: drop-shadow(0 10px 20px rgb(90 80 200 / 0.3));
  margin-bottom: 6px;
}
h1 {
  font-size: clamp(30px, 4.4vw, 44px);
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.08;
  background: linear-gradient(180deg, var(--text-1), color-mix(in srgb, var(--text-1) 78%, var(--accent)));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.subtitle {
  margin: 6px 0 0;
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--text-2);
}
.subtitle::before,
.subtitle::after {
  content: '';
  width: 46px;
  height: 1px;
  background: currentColor;
  opacity: 0.4;
}
.title-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  max-width: 100%;
}
.title-row.right {
  flex-direction: row-reverse;
}
.logo.side {
  width: clamp(38px, 4.6vw, 52px);
  height: clamp(38px, 4.6vw, 52px);
  margin: 0;
  flex: none;
}
.compact .logo.side {
  width: 40px;
  height: 40px;
}
.logo.custom {
  object-fit: contain;
  border-radius: 14px;
}
.compact .logo {
  width: 44px;
  height: 44px;
}
@media (max-width: 699px) {
  .subtitle {
    letter-spacing: 0.2em;
    font-size: 11px;
  }
  .subtitle::before,
  .subtitle::after {
    width: 22px;
  }
}
</style>
