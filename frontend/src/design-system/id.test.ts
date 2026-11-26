import { describe, expect, it } from 'vitest'
import { randomHex } from './id'

describe('randomHex', () => {
  it('donne 12 caractères hexadécimaux par défaut', () => {
    expect(randomHex()).toMatch(/^[0-9a-f]{12}$/)
  })
  it('respecte la longueur demandée et varie', () => {
    expect(randomHex(5)).toMatch(/^[0-9a-f]{5}$/)
    expect(randomHex()).not.toBe(randomHex())
  })
})
