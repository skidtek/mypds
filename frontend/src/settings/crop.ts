/** Calculs du cadrage de la photo de profil (fonctions pures, testées). */
export interface Size {
  w: number
  h: number
}
export interface Point {
  x: number
  y: number
}

/** Échelle à laquelle l'image couvre juste le carré de cadrage. */
export function coverScale(n: Size, view: number): number {
  return n.w && n.h ? Math.max(view / n.w, view / n.h) : 1
}

/** Empêche de laisser un vide dans le cercle : l'image doit toujours couvrir la zone. */
export function clampOffset(o: Point, n: Size, scale: number, view: number): Point {
  const mx = Math.max(0, (n.w * scale - view) / 2)
  const my = Math.max(0, (n.h * scale - view) / 2)
  return { x: Math.min(mx, Math.max(-mx, o.x)), y: Math.min(my, Math.max(-my, o.y)) }
}

/** Carré de l'image d'origine (en pixels de l'image) visible dans la zone de cadrage. */
export function cropRect(n: Size, scale: number, o: Point, view: number): { x: number; y: number; size: number } {
  const size = view / scale
  return { x: (n.w * scale - view) / 2 / scale - o.x / scale, y: (n.h * scale - view) / 2 / scale - o.y / scale, size }
}
