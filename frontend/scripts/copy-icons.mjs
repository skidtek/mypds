// Copie les logos Simple Icons (CC0) dans public/icons/simple/ et produit un index léger
// {s: slug, t: titre, h: couleur}. Chargés un par un à la demande : rien n'alourdit le bundle.
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const src = join(root, 'node_modules/simple-icons')
const out = join(root, 'public/icons/simple')
const data = JSON.parse(readFileSync(join(src, 'data/simple-icons.json'), 'utf8'))
const icons = Array.isArray(data) ? data : data.icons
const titleToSlug = (t) =>
  t.toLowerCase().replace(/\+/g, 'plus').replace(/\./g, 'dot').replace(/&/g, 'and').replace(/đ/g, 'd').replace(/ħ/g, 'h')
    .replace(/ı/g, 'i').replace(/ĸ/g, 'k').replace(/ŀ/g, 'l').replace(/ł/g, 'l').replace(/ß/g, 'ss').replace(/ŧ/g, 't')
    .normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]/g, '')

mkdirSync(out, { recursive: true })
const index = []
for (const icon of icons) {
  const slug = icon.slug || titleToSlug(icon.title)
  const file = join(src, 'icons', `${slug}.svg`)
  if (!existsSync(file)) continue
  copyFileSync(file, join(out, `${slug}.svg`))
  index.push({ s: slug, t: icon.title, h: icon.hex })
}
writeFileSync(join(out, 'index.json'), JSON.stringify(index))
const pkg = JSON.parse(readFileSync(join(src, 'package.json'), 'utf8'))
writeFileSync(join(out, 'LICENSE.txt'), `Simple Icons ${pkg.version} — CC0-1.0 (https://simpleicons.org).\nLes marques restent la propriété de leurs détenteurs.\n`)
console.log(`simple-icons : ${index.length} logos copiés`)
