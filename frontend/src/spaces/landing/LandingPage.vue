<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import BrandHeader from '@/app/BrandHeader.vue'
import TopBar from '@/app/TopBar.vue'
import type { WidgetType } from '@/api/types'
import { useLanding } from '@/stores/landing'
import CockpitHandle from './CockpitHandle.vue'
import EditToolbar from './EditToolbar.vue'
import { breakpointFor } from './grid'
import LandingGrid from './LandingGrid.vue'
import LibraryDialog from './LibraryDialog.vue'
import WidgetConfigDialog from './WidgetConfigDialog.vue'

const store = useLanding()
const vw = ref(window.innerWidth)
const bp = computed(() => breakpointFor(vw.value))
const library = ref(false)
const configuring = ref<string | null>(null)
const loadError = ref('')
const configWidget = computed(() => (configuring.value ? store.widget(configuring.value) : undefined))

const onResize = () => (vw.value = window.innerWidth)
onMounted(async () => {
  window.addEventListener('resize', onResize, { passive: true })
  try {
    await store.load()
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e)
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  void store.flush()
  store.editing = false
})

function add(type: WidgetType) {
  library.value = false
  const id = store.addWidget(type)
  if (type === 'weather') configuring.value = id
}

async function done() {
  store.editing = false
  await store.flush()
}
</script>

<template>
  <div class="landing" :class="{ editing: store.editing }">
    <TopBar
      editable
      :editing="store.editing"
      :edit-label="store.editing ? $t('Terminer') : $t('Personnaliser ma Home')"
      :settings-label="$t('Réglages de la Home')"
      @edit="store.editing ? done() : (store.editing = true)"
    />
    <main class="content">
      <BrandHeader />
      <p v-if="loadError" class="load-error glass">{{ $t('Impossible de charger votre page : {error}', { error: loadError }) }}</p>
      <div v-else-if="store.doc" class="grid-area">
        <LandingGrid :key="bp" :bp="bp" @configure="configuring = $event" />
      </div>
      <button v-if="store.doc && !store.widgets.some((w) => !w.hidden)" class="btn empty-add" type="button" @click="store.editing = true; library = true">
        {{ $t('Votre page est vide — ajouter un widget') }}
      </button>
    </main>
    <CockpitHandle v-if="!store.editing" />
    <div v-else class="toolbar-space" />

    <EditToolbar v-if="store.editing" :bp="bp" @add="library = true" @done="done" />
    <LibraryDialog v-if="library" @close="library = false" @add="add" />
    <WidgetConfigDialog v-if="configWidget" :widget="configWidget" @close="configuring = null" />
  </div>
</template>

<style scoped>
.landing {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
}
.content {
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  padding: 8px 32px 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}
/* Les tuiles flottent au centre de l'espace libre entre le titre et le bouton du cockpit */
.grid-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 12px 0 24px;
}
.load-error {
  padding: 20px;
  text-align: center;
}
.empty-add {
  margin: 24px auto;
  display: flex;
}
.toolbar-space {
  height: 140px;
}
@media (max-width: 1023px) {
  .content {
    padding: 4px 24px 0;
  }
}
@media (max-width: 699px) {
  .content {
    padding: 0 14px;
  }
}
</style>
