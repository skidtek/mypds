<script setup lang="ts">
import { PhArrowCounterClockwise, PhCheck, PhEye, PhPlus } from '@phosphor-icons/vue'
import { computed, ref } from 'vue'
import { useLanding } from '@/stores/landing'
import { t, tk } from '@/i18n'
import { WIDGET_NAMES } from '@/widgets/names'

defineProps<{ bp: 'desktop' | 'tablet' | 'mobile' }>()
const emit = defineEmits<{ add: []; done: [] }>()
const store = useLanding()
const showHidden = ref(false)
const confirmReset = ref(false)

const statusText = computed(
  () =>
    ({
      idle: t('Glissez les widgets pour les déplacer'),
      saving: t('Enregistrement…'),
      saved: t('Modifications enregistrées'),
      error: t("Échec de l'enregistrement : {error}", { error: store.error }),
      conflict: t('Modifiée ailleurs : rechargez la page'),
    })[store.status],
)
const NAMES = WIDGET_NAMES
const bpLabel = { desktop: tk('Disposition ordinateur'), tablet: tk('Disposition tablette'), mobile: tk('Disposition mobile') }

async function reset() {
  if (!confirmReset.value) {
    confirmReset.value = true
    return
  }
  confirmReset.value = false
  await store.reset()
}
</script>

<template>
  <div class="toolbar glass glass-strong" role="toolbar" :aria-label="$t('Personnaliser ma Home')">
    <div class="status" aria-live="polite">
      <strong>{{ $t(bpLabel[bp]) }}</strong>
      <span :class="{ 'error-text': store.status === 'error' || store.status === 'conflict' }">{{ statusText }}</span>
    </div>
    <div class="tools">
      <button class="btn small" type="button" @click="emit('add')"><PhPlus :size="15" weight="bold" /> {{ $t('Ajouter') }}</button>
      <div v-if="store.hidden.length" class="hidden-wrap">
        <button class="btn small" type="button" :aria-expanded="showHidden" @click="showHidden = !showHidden">
          <PhEye :size="15" /> {{ $t('Masqués ({n})', { n: store.hidden.length }) }}
        </button>
        <ul v-if="showHidden" class="pop glass glass-strong">
          <li v-for="w in store.hidden" :key="w.id">
            <span>{{ w.title || $t(NAMES[w.type]) }}</span>
            <button class="btn small" type="button" @click="store.setHidden(w.id, false)">{{ $t('Afficher') }}</button>
          </li>
        </ul>
      </div>
      <button v-if="bp === 'mobile' && store.doc?.mobile.mode === 'custom'" class="btn small" type="button" @click="store.resetMobile()">
        {{ $t('Ordre automatique') }}
      </button>
      <button class="btn small" :class="{ danger: confirmReset }" type="button" @click="reset" @blur="confirmReset = false">
        <PhArrowCounterClockwise :size="15" /> {{ confirmReset ? $t('Confirmer ?') : $t('Réinitialiser') }}
      </button>
      <button class="btn small primary" type="button" @click="emit('done')"><PhCheck :size="15" weight="bold" /> {{ $t('Terminé') }}</button>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  position: fixed;
  left: 50%;
  bottom: calc(18px + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 10px 10px 10px 20px;
  border-radius: 22px;
  box-shadow: var(--shadow-float);
  width: max-content;
  max-width: calc(100vw - 24px);
  animation: rise var(--dur) var(--ease);
}
@keyframes rise {
  from {
    opacity: 0;
    transform: translate(-50%, 16px);
  }
}
.status {
  display: grid;
  font-size: 12.5px;
  min-width: 0;
}
.status strong {
  font-size: 13.5px;
}
.status span {
  color: var(--text-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 260px;
}
.tools {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.hidden-wrap {
  position: relative;
}
.pop {
  position: absolute;
  bottom: calc(100% + 10px);
  left: 0;
  list-style: none;
  margin: 0;
  padding: 8px;
  min-width: 240px;
  border-radius: var(--radius-md);
  display: grid;
  gap: 4px;
}
.pop li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 4px 4px 4px 8px;
  font-size: 14px;
}
@media (max-width: 699px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    padding: 12px;
    width: calc(100vw - 24px);
  }
  .tools {
    justify-content: flex-start;
  }
}
</style>
