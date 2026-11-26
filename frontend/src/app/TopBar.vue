<script setup lang="ts">
import { PhGearSix, PhHouse, PhSignOut, PhSlidersHorizontal, PhUser, PhUserCircle } from '@phosphor-icons/vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { avatarUrl, useSession } from '@/stores/session'

defineProps<{ editable?: boolean; editing?: boolean; editLabel?: string; settingsSection?: string; settingsLabel?: string }>()
const emit = defineEmits<{ edit: [] }>()
const session = useSession()
const router = useRouter()
const menu = ref(false)
const root = ref<HTMLElement>()
const photo = computed(() => (session.me ? avatarUrl(session.me) : null))

async function logout() {
  await session.logout()
  void router.replace({ name: 'login' })
}
function onDoc(e: MouseEvent) {
  if (menu.value && root.value && !root.value.contains(e.target as Node)) menu.value = false
}
onMounted(() => document.addEventListener('click', onDoc))
onBeforeUnmount(() => document.removeEventListener('click', onDoc))
</script>

<template>
  <nav ref="root" class="topbar" :aria-label="$t('Navigation principale')">
    <RouterLink class="icon-btn" :to="{ name: 'landing' }" :aria-label="$t('Accueil')"><PhHouse :size="20" /></RouterLink>
    <slot />
    <div class="right">
      <!-- Bouton propre à l'espace affiché : « Personnaliser ma Home » ou « Modifier le Cockpit » -->
      <button
        v-if="editable"
        type="button"
        class="edit-btn"
        :class="{ active: editing }"
        :aria-pressed="editing"
        :title="editLabel"
        @click="emit('edit')"
      >
        <PhSlidersHorizontal :size="18" />
        <span class="lbl">{{ editLabel }}</span>
      </button>
      <RouterLink
        class="icon-btn"
        :to="{ name: 'settings', query: settingsSection ? { section: settingsSection } : {} }"
        :aria-label="settingsLabel ?? $t('Réglages')"
        :title="settingsLabel ?? $t('Réglages')"
      >
        <PhGearSix :size="20" />
      </RouterLink>
      <div class="account">
        <button type="button" class="icon-btn" aria-haspopup="menu" :aria-expanded="menu" :aria-label="$t('Compte')" @click="menu = !menu">
          <img v-if="photo" class="avatar" :src="photo" alt="" width="26" height="26" />
          <PhUserCircle v-else :size="22" weight="fill" />
        </button>
        <div v-if="menu" class="menu glass glass-strong" role="menu">
          <p class="who">
            <strong>{{ session.me?.display_name }}</strong>
            <span class="faint">{{ session.me?.username }}</span>
          </p>
          <RouterLink role="menuitem" class="item" :to="{ name: 'settings', query: { section: 'profile' } }" @click="menu = false">
            <PhUser :size="16" /> {{ $t('Mon profil') }}
          </RouterLink>
          <button type="button" role="menuitem" @click="logout"><PhSignOut :size="16" /> {{ $t('Se déconnecter') }}</button>
        </div>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
}
.edit-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 14px 0 12px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--surface-border);
  background: var(--surface);
  -webkit-backdrop-filter: blur(var(--blur));
  backdrop-filter: blur(var(--blur));
  color: var(--text-1);
  font-size: 13.5px;
  font-weight: 600;
  white-space: nowrap;
  transition: background var(--dur-fast);
}
.edit-btn:hover {
  background: var(--surface-hover);
}
.edit-btn.active {
  background: var(--accent);
  border-color: transparent;
  color: #fff;
}
@media (max-width: 699px) {
  .edit-btn .lbl {
    display: none;
  }
  .edit-btn {
    padding: 0;
    width: 36px;
    justify-content: center;
  }
}
.right {
  margin-left: auto;
  display: flex;
  gap: 4px;
  align-items: center;
}
.account {
  position: relative;
}
.menu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 210px;
  padding: 8px;
  border-radius: var(--radius-md);
  z-index: 40;
}
.who {
  display: grid;
  margin: 4px 8px 8px;
  font-size: 14px;
}
.menu button,
.menu .item {
  width: 100%;
  color: inherit;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 8px;
  border: none;
  background: none;
  padding: 9px 10px;
  border-radius: 10px;
  font-size: 14px;
}
.menu button:hover,
.menu .item:hover {
  background: var(--accent-soft);
}
.avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  object-fit: cover;
}
</style>
