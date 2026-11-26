import { describe, expect, it } from 'vitest'
import type { WeatherReport } from '@/api/types'
import { rainExpected, sunProgress, uvLevel, windFrom, windValue } from './metrics'

const report = (over: Partial<WeatherReport['current']> = {}, day: Partial<WeatherReport['days'][number]> = {}): WeatherReport => ({
  provider: 'open-meteo',
  attribution: '',
  timezone: 'Europe/Paris',
  utc_offset_seconds: 3600,
  unit: 'celsius',
  fetched_at: '2026-11-25T12:00:00Z',
  current: { temperature: 4, apparent_temperature: null, condition: 'cloudy', label: '', is_day: true, humidity: null, wind_speed: 10, wind_gusts: null, wind_direction: null, precipitation: 0, ...over },
  days: [{ date: '2026-11-25', condition: 'cloudy', label: '', temp_min: 2, temp_max: 6, sunrise: '08:00', sunset: '17:00', precipitation_sum: 0, precipitation_probability: 10, uv_index_max: 1, wind_max: 20, ...day }],
  air: null,
})

describe('météo', () => {
  it('place le soleil selon l’heure locale du lieu', () => {
    // 11:30 UTC = 12:30 à Paris : milieu de journée (lever 8 h, coucher 17 h)
    expect(sunProgress(report(), Date.UTC(2026, 10, 25, 11, 30))).toBeCloseTo(0.5, 2)
    expect(sunProgress(report(), Date.UTC(2026, 10, 25, 22, 0))).toBeGreaterThan(1)
  })
  it('affiche la pluie si elle est en cours ou attendue, sinon le vent', () => {
    expect(rainExpected(report())).toBe(false)
    expect(rainExpected(report({}, { precipitation_probability: 60 }))).toBe(true)
    expect(rainExpected(report({ condition: 'snow' }))).toBe(true)
    expect(rainExpected(report({ precipitation: 0.2 }))).toBe(true)
  })
  it('classe l’UV et le vent', () => {
    expect([1, 3, 6, 9, 11].map(uvLevel)).toEqual([0, 1, 2, 3, 4])
    expect(windFrom(250)).toBe('O')
    expect(windFrom(359)).toBe('N')
    expect(windValue(16.09, 'fahrenheit')).toEqual({ value: 10, unit: 'mph' })
  })
})
