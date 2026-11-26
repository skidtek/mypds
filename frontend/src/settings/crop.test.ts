import { describe, expect, it } from 'vitest'
import { clampOffset, coverScale, cropRect } from './crop'

describe('cadrage de la photo', () => {
  const portrait = { w: 1000, h: 2000 }
  it('couvre la zone sans vide', () => {
    expect(coverScale(portrait, 250)).toBe(0.25)
    // largeur affichée = 250 : pas de marge horizontale ; hauteur 500 : 125 px de chaque côté
    expect(clampOffset({ x: 80, y: 400 }, portrait, 0.25, 250)).toEqual({ x: 0, y: 125 })
  })
  it('centre par défaut, puis suit le déplacement', () => {
    expect(cropRect(portrait, 0.25, { x: 0, y: 0 }, 250)).toEqual({ x: 0, y: 500, size: 1000 })
    // image descendue de 125 px à l'écran = on voit le haut de la photo (la tête)
    expect(cropRect(portrait, 0.25, { x: 0, y: 125 }, 250)).toEqual({ x: 0, y: 0, size: 1000 })
    // zoom ×2 : carré deux fois plus petit, toujours centré
    expect(cropRect(portrait, 0.5, { x: 0, y: 0 }, 250)).toEqual({ x: 250, y: 750, size: 500 })
  })
})
