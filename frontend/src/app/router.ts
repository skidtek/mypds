import { createRouter, createWebHistory } from 'vue-router'
import { useSession } from '@/stores/session'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'landing', component: () => import('@/spaces/landing/LandingPage.vue') },
    { path: '/cockpit/:group?', name: 'cockpit', component: () => import('@/spaces/cockpit/CockpitPage.vue') },
    { path: '/reglages', name: 'settings', component: () => import('@/settings/SettingsPage.vue') },
    { path: '/connexion', name: 'login', component: () => import('@/app/LoginPage.vue'), meta: { public: true } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const session = useSession()
  if (!session.checked) {
    try {
      await session.refresh()
    } catch {
      /* serveur injoignable : la page de connexion affichera l'erreur */
    }
  }
  if (!to.meta.public && !session.me) return { name: 'login', query: to.fullPath !== '/' ? { next: to.fullPath } : {} }
  if (to.name === 'login' && session.me) return { name: 'landing' }
})
