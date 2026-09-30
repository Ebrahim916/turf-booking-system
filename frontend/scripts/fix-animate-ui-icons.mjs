/**
 * Post-processing for files pulled from the animate-ui icon registry.
 *
 * The registry emits `import * as React from 'react'` on every icon and imports
 * Motion's `Variants` as a value. Under this project's `verbatimModuleSyntax` +
 * `noUnusedLocals` settings that is a type error, so the two lines are rewritten
 * in place after `shadcn add` instead of patching 50+ generated files by hand.
 *
 * Re-run after adding more icons:
 *   node scripts/fix-animate-ui-icons.mjs
 */
import { readdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'

const ICONS_DIR = path.resolve('src/components/animate-ui/icons')

const files = (await readdir(ICONS_DIR)).filter(
  (name) => name.endsWith('.tsx') && name !== 'icon.tsx',
)

let changed = 0

for (const name of files) {
  const file = path.join(ICONS_DIR, name)
  const original = await readFile(file, 'utf8')
  let next = original

  // `Variants` and `UseInViewOptions` are types, not values.
  next = next.replace(
    /import \{ motion, type Variants \} from 'motion\/react';/,
    "import { motion, type Variants } from 'motion/react';",
  )
  next = next.replace(
    /import \{ motion, Variants \} from 'motion\/react';/,
    "import { motion, type Variants } from 'motion/react';",
  )
  next = next.replace(
    /import \{ motion, UseInViewOptions \} from 'motion\/react';/,
    "import { motion, type UseInViewOptions } from 'motion/react';",
  )

  // Drop the unused React namespace import, but only when `React.` is never
  // referenced in the file.
  if (!/\bReact\./.test(next)) {
    next = next.replace(/import \* as React from 'react';\n\n?/, '')
  }

  if (next !== original) {
    await writeFile(file, next, 'utf8')
    changed += 1
  }
}

console.log(`fixed ${changed}/${files.length} animate-ui icon files`)
