/**
 * Identifiant aléatoire hexadécimal (12 caractères = 48 bits).
 * `crypto.randomUUID()` n'existe qu'en contexte sécurisé (HTTPS ou localhost) : en essai HTTP
 * sur une IP du LAN il est absent. `crypto.getRandomValues()` est disponible partout.
 */
export function randomHex(chars = 12): string {
  const bytes = crypto.getRandomValues(new Uint8Array(Math.ceil(chars / 2)))
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('').slice(0, chars)
}
