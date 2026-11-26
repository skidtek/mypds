import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import en from './en'
import { extractKeys } from './extract'
import { locale, t, tn } from './index'

const SRC = resolve(__dirname, '..')

describe('catalogue anglais', () => {
  const keys = extractKeys(SRC)

  it('traduit tous les textes de l’interface', () => {
    const missing = [...keys].filter((k) => !(k in en)).sort()
    expect(missing).toEqual([])
  })

  it('garde les mêmes paramètres {…} dans la traduction', () => {
    const params = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(',')
    const wrong = Object.entries(en).filter(([fr, tr]) => params(fr) !== params(tr)).map(([fr]) => fr)
    expect(wrong).toEqual([])
  })

  it('n’a pas de traduction orpheline', () => {
    const orphans = Object.keys(en).filter((k) => !keys.has(k))
    expect(orphans).toEqual([])
  })

  it('bascule de langue et accorde le pluriel', () => {
    locale.value = 'en'
    expect(t('Réglages')).toBe('Settings')
    expect(tn(1, '{n} service', '{n} services')).toBe('1 service')
    expect(tn(0, '{n} service', '{n} services')).toBe('0 services')
    locale.value = 'fr'
    expect(t('Réglages')).toBe('Réglages')
    expect(tn(0, '{n} service', '{n} services')).toBe('0 service')
  })
})
