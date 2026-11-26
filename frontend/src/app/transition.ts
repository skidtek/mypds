/**
 * Passage Home ⇄ Cockpit : instantané, sans animation (choix de l'utilisateur, 2026-11-25).
 * Le Cockpit est préchargé depuis la Home, l'affichage est donc immédiat.
 */
import { nextTick, ref } from 'vue'
import type { Router } from 'vue-router'

/** Vrai pendant une navigation instantanée : App.vue désactive alors la transition de page. */
export const instantNav = ref(false)

export async function navigateInstant(router: Router, to: string) {
  instantNav.value = true
  try {
    await router.push(to)
    await nextTick()
  } finally {
    instantNav.value = false // les autres navigations gardent le fondu court
  }
}
