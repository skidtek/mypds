<script setup lang="ts">
import { PhArrowClockwise, PhArrowUpRight, PhCaretLeft, PhCaretRight, PhRss } from '@phosphor-icons/vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { RssItem, Widget } from '@/api/types'
import { ago } from '@/design-system/time'
import { usePolling } from '@/design-system/usePolling'
import WidgetHeader from '../WidgetHeader.vue'

const props = defineProps<{ widget: Widget; editing: boolean }>()
const router = useRouter()
const items = ref<RssItem[] | null>(null)
const error = ref('')
const track = ref<HTMLElement>()
const page = ref(0)
const pages = ref(1)
const broken = ref(new Set<string>())

const cfg = computed(() => props.widget.config as { category_ids: string[] | null; count: number })

async function load() {
  try {
    const q = new URLSearchParams({ limit: String(cfg.value.count) })
    for (const id of cfg.value.category_ids ?? []) q.append('category_id', id)
    items.value = await api<RssItem[]>(`/api/v1/rss/items?${q}`)
    error.value = ''
    requestAnimationFrame(measure)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

const { refresh } = usePolling(load, 10 * 60 * 1000)
watch(cfg, () => void refresh(), { deep: true })

function measure() {
  const el = track.value
  if (!el) return
  pages.value = Math.max(1, Math.round(el.scrollWidth / el.clientWidth))
  page.value = Math.min(pages.value - 1, Math.round(el.scrollLeft / el.clientWidth))
}

function go(p: number) {
  const el = track.value
  if (!el) return
  const target = Math.max(0, Math.min(pages.value - 1, p))
  el.scrollTo({ left: target * el.clientWidth, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
}

let ro: ResizeObserver | undefined
onMounted(() => {
  ro = new ResizeObserver(measure)
  if (track.value) ro.observe(track.value)
})
onBeforeUnmount(() => ro?.disconnect())
watch(track, (el) => el && ro?.observe(el))

const hue = (s: string) => [...s].reduce((a, c) => a + c.charCodeAt(0), 0) % 360
function openSettings() {
  void router.push({ name: 'settings', query: { section: 'news' } })
}
</script>

<template>
  <div class="news">
    <WidgetHeader :title="widget.title || $t('News')">
      <template #icon><PhRss :size="22" /></template>
      <template #right>
        <button class="feeds-link" type="button" :disabled="editing" @click="openSettings">
          {{ $t('Mes flux RSS') }} <PhArrowUpRight :size="14" />
        </button>
      </template>
    </WidgetHeader>

    <div v-if="error" class="empty">
      <p>{{ $t('Actualités indisponibles.') }}<br /><span class="faint">{{ error }}</span></p>
      <button class="btn small" type="button" @click="refresh()"><PhArrowClockwise :size="14" /> {{ $t('Réessayer') }}</button>
    </div>
    <div v-else-if="items && !items.length" class="empty">
      <p>{{ $t('Aucun article pour l\'instant.') }}</p>
      <button class="btn small" type="button" :disabled="editing" @click="openSettings">{{ $t('Ajouter des flux ou importer un OPML') }}</button>
    </div>
    <template v-else-if="items">
      <div class="carousel">
        <ul ref="track" class="track" @scroll.passive="measure">
          <li v-for="it in items" :key="it.id">
            <a class="card" :href="it.link ?? undefined" target="_blank" rel="noopener noreferrer" :tabindex="editing ? -1 : 0">
              <div class="thumb" :style="{ '--h': hue(it.source) }">
                <img
                  v-if="it.image && !broken.has(it.id)"
                  :src="it.image"
                  alt=""
                  loading="lazy"
                  decoding="async"
                  @error="broken.add(it.id)"
                />
                <span v-else class="initial" aria-hidden="true">{{ it.source.slice(0, 1) }}</span>
              </div>
              <div class="meta">
                <span class="src">{{ it.source }} · {{ ago(it.published_at) }}</span>
                <strong class="ttl">{{ it.title }}</strong>
              </div>
            </a>
          </li>
        </ul>
        <button v-if="page > 0" class="nav prev glass" type="button" :aria-label="$t('Articles précédents')" @click="go(page - 1)">
          <PhCaretLeft :size="16" weight="bold" />
        </button>
        <button v-if="page < pages - 1" class="nav next glass" type="button" :aria-label="$t('Articles suivants')" @click="go(page + 1)">
          <PhCaretRight :size="16" weight="bold" />
        </button>
      </div>
      <div v-if="pages > 1" class="dots" role="tablist" :aria-label="$t('Pages d\'articles')">
        <button
          v-for="p in pages"
          :key="p"
          type="button"
          role="tab"
          :aria-selected="p - 1 === page"
          :aria-label="$t('Page {n}', { n: p })"
          @click="go(p - 1)"
        />
      </div>
    </template>
    <div v-else class="skeleton" aria-busy="true" :aria-label="$t('Chargement des actualités')" />
  </div>
</template>

<style scoped>
.news {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  container-type: size;
}
.feeds-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: none;
  color: var(--text-2);
  font-size: 13.5px;
  font-weight: 560;
  padding: 2px 0;
}
.feeds-link:hover {
  color: var(--text-1);
}
.carousel {
  position: relative;
  flex: 1;
  min-height: 0;
}
.track {
  --per: 3;
  --gap: 14px;
  list-style: none;
  margin: 0;
  padding: 0;
  height: 100%;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: calc((100% - (var(--per) - 1) * var(--gap)) / var(--per));
  gap: var(--gap);
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  scrollbar-width: none;
  overscroll-behavior-x: contain;
}
.track::-webkit-scrollbar {
  display: none;
}
.track li {
  scroll-snap-align: start;
  min-height: 0;
}
.card {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 18px;
  overflow: hidden;
  background: var(--surface-strong);
  border: 1px solid var(--surface-border);
  box-shadow: 0 6px 18px -10px rgb(24 32 64 / 0.3);
  transition: transform var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 28px -14px rgb(24 32 64 / 0.4);
}
.thumb {
  flex: 1 1 55%;
  min-height: 60px;
  position: relative;
  background: linear-gradient(135deg, hsl(var(--h) 60% 78%), hsl(calc(var(--h) + 40) 55% 68%));
  display: grid;
  place-items: center;
}
.thumb img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.initial {
  font-size: 32px;
  font-weight: 700;
  color: rgb(255 255 255 / 0.9);
}
.meta {
  padding: 10px 12px 12px;
  display: grid;
  gap: 4px;
}
.src {
  font-size: 11.5px;
  color: var(--text-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ttl {
  font-size: 13.5px;
  font-weight: 650;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.nav {
  position: absolute;
  top: 38%;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  opacity: 0;
  transition: opacity var(--dur-fast);
  color: var(--text-1);
  padding: 0;
}
.prev {
  left: -10px;
}
.next {
  right: -10px;
}
.carousel:hover .nav,
.nav:focus-visible {
  opacity: 1;
}
.dots {
  display: flex;
  justify-content: center;
  gap: 8px;
}
.dots button {
  width: 7px;
  height: 7px;
  padding: 0;
  border-radius: 50%;
  border: none;
  background: var(--text-3);
  opacity: 0.45;
  transition: opacity var(--dur-fast), transform var(--dur-fast);
}
.dots button[aria-selected='true'] {
  opacity: 1;
  background: var(--text-2);
  transform: scale(1.15);
}
.empty {
  flex: 1;
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
@container (max-width: 640px) {
  .track {
    --per: 2;
  }
}
@container (max-width: 400px) {
  .track {
    --per: 1.25;
  }
}
@container (min-width: 1000px) {
  .track {
    --per: 4;
  }
}
@media (hover: none) {
  .nav {
    display: none;
  }
}
</style>
