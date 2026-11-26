<script setup lang="ts">
import { PhCaretLeft, PhCalendarBlank, PhGauge, PhPlugsConnected, PhLayout, PhMagnifyingGlass, PhPaintBrush, PhRss, PhTagSimple, PhUser } from '@phosphor-icons/vue'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TopBar from '@/app/TopBar.vue'
import { useSession } from '@/stores/session'
import AppearanceSection from './AppearanceSection.vue'
import BrandingSection from './BrandingSection.vue'
import CalendarSection from './CalendarSection.vue'
import CockpitSection from './CockpitSection.vue'
import ConnectorsSection from './ConnectorsSection.vue'
import LayoutSection from './LayoutSection.vue'
import NewsSection from './NewsSection.vue'
import ProfileSection from './ProfileSection.vue'
import SearchSection from './SearchSection.vue'
import { t, tk } from '@/i18n'

const route = useRoute()
const router = useRouter()
const session = useSession()

// Réglages regroupés par espace : la Home et le Cockpit ont chacun les leurs
const SECTIONS = computed(() => [
  { id: 'profile', label: tk('Mon profil'), icon: PhUser, comp: ProfileSection, space: tk('Compte') },
  { id: 'appearance', label: tk('Apparence'), icon: PhPaintBrush, comp: AppearanceSection, space: tk('Général') },
  { id: 'search', label: tk('Recherche'), icon: PhMagnifyingGlass, comp: SearchSection, space: 'Home' },
  { id: 'agenda', label: tk('Agenda'), icon: PhCalendarBlank, comp: CalendarSection, space: 'Home' },
  { id: 'news', label: tk('Actualités'), icon: PhRss, comp: NewsSection, space: 'Home' },
  { id: 'layout', label: tk('Disposition'), icon: PhLayout, comp: LayoutSection, space: 'Home' },
  { id: 'cockpit', label: tk('Cockpit'), icon: PhGauge, comp: CockpitSection, space: 'Cockpit' },
  ...(session.me?.role === 'admin'
    ? [
        { id: 'connectors', label: tk('Connexions'), icon: PhPlugsConnected, comp: ConnectorsSection, space: 'Cockpit' },
        { id: 'branding', label: tk('Marque'), icon: PhTagSimple, comp: BrandingSection, space: tk('Général') },
      ]
    : []),
])
const SPACES = ['Home', 'Cockpit', tk('Général'), tk('Compte')]
const grouped = computed(() => SPACES.map((sp) => ({ space: sp, items: SECTIONS.value.filter((x) => x.space === sp) })).filter((g) => g.items.length))
const current = computed(() => SECTIONS.value.find((s) => s.id === route.query.section) ?? SECTIONS.value[0]!)
const select = (id: string) => void router.replace({ query: { section: id } })

// Retour vers la page d'origine (Home ou Cockpit) ; les changements de section ne comptent pas
const origin = typeof window !== 'undefined' ? (window.history.state?.back as string | null) : null
const backTo = origin && !origin.startsWith('/reglages') && !origin.startsWith('/connexion') ? origin : '/'
const backLabel = computed(() => (backTo.startsWith('/cockpit') ? t('Retour au Cockpit') : t("Retour à l'accueil")))
function goBack() {
  void router.push(backTo)
}
</script>

<template>
  <div class="settings">
    <TopBar />
    <main class="wrap">
      <div class="head">
        <button class="back glass" type="button" :aria-label="backLabel" :title="backLabel" @click="goBack">
          <PhCaretLeft :size="18" weight="bold" />
        </button>
        <h1>{{ $t('Réglages') }}</h1>
      </div>
      <div class="layout">
        <nav class="nav glass" :aria-label="$t('Sections des réglages')">
          <template v-for="g in grouped" :key="g.space">
            <p class="nav-title">{{ $t(g.space) }}</p>
            <button
              v-for="s in g.items"
              :key="s.id"
              type="button"
              :aria-current="s.id === current.id ? 'page' : undefined"
              @click="select(s.id)"
            >
              <component :is="s.icon" :size="18" />
              <span>{{ $t(s.label) }}</span>
            </button>
          </template>
        </nav>
        <div class="panel glass">
          <component :is="current.comp" :key="current.id" />
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.settings {
  min-height: 100dvh;
}
.wrap {
  max-width: 1040px;
  margin: 0 auto;
  padding: 0 32px 48px;
}
.head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 4px 0 20px;
}
h1 {
  font-size: 30px;
  font-weight: 700;
}
.back {
  border: 1px solid var(--surface-border);
  padding: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: var(--text-1);
  flex: none;
  transition: transform var(--dur-fast) var(--ease), box-shadow var(--dur-fast);
}
.back:hover {
  transform: translateX(-2px);
  box-shadow: var(--shadow-float);
}
.back:focus-visible {
  border-radius: 50%;
}
.layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 20px;
  align-items: start;
}
.nav {
  display: grid;
  gap: 2px;
  padding: 8px;
  position: sticky;
  top: 16px;
}
.nav-title {
  margin: 8px 12px 2px;
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-3);
}
.nav-title:first-child {
  margin-top: 2px;
}
.nav button {
  display: flex;
  align-items: center;
  gap: 10px;
  border: none;
  background: none;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 14.5px;
  font-weight: 560;
  color: var(--text-2);
  text-align: left;
}
.nav button:hover {
  background: var(--surface-hover);
  color: var(--text-1);
}
.nav button[aria-current='page'] {
  background: var(--accent-soft);
  color: var(--accent);
}
.panel {
  padding: 26px 28px;
  min-width: 0;
}
.panel :deep(.sec) {
  display: grid;
  gap: 18px;
}
.panel :deep(.sec h2) {
  font-size: 21px;
  font-weight: 680;
}
@media (max-width: 799px) {
  .wrap {
    padding: 0 14px 40px;
  }
  .layout {
    grid-template-columns: 1fr;
  }
  .nav {
    position: static;
    display: flex;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .nav-title {
  margin: 8px 12px 2px;
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-3);
}
.nav-title:first-child {
  margin-top: 2px;
}
.nav button {
    flex: none;
  }
  .panel {
    padding: 20px 18px;
  }
}
</style>
