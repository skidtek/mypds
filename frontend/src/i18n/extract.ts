/** Extraction des textes à traduire (utilisée par le test de complétude du catalogue). */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

const STR = `('(?:[^'\\\\]|\\\\.)*'|"(?:[^"\\\\]|\\\\.)*")`
const CALL = new RegExp(`(?:\\$t|\\bt|\\btk|\\btr)\\(\\s*${STR}`, 'g')
const PLURAL = new RegExp(`\\$?tn\\([^,()]+(?:\\([^()]*\\))?[^,()]*,\\s*${STR}\\s*,\\s*${STR}`, 'g')

const unquote = (lit: string) => lit.slice(1, -1).replace(/\\(.)/g, '$1')

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) {
      if (name !== 'i18n') walk(p, out)
    } else if (/\.(vue|ts)$/.test(name) && !name.endsWith('.test.ts')) out.push(p)
  }
  return out
}

export function extractKeys(root: string): Set<string> {
  const keys = new Set<string>()
  for (const file of walk(root)) {
    const src = readFileSync(file, 'utf8')
    for (const m of src.matchAll(CALL)) keys.add(unquote(m[1]!))
    for (const m of src.matchAll(PLURAL)) {
      keys.add(unquote(m[1]!))
      keys.add(unquote(m[2]!))
    }
  }
  return keys
}
