# Frontend

React SPA for the Turf Booking System. Minimalist visual language, animated
icons from [animate-ui](https://animate-ui.com), and
[thinking-orbs](https://orbs.jakubantalik.com) for every loading state.

## Stack

| Concern | Choice |
|---|---|
| Build | Vite 8 + React 19 + TypeScript (strict) |
| Routing | react-router 7 |
| Styling | Tailwind CSS v4 (CSS-first `@theme`) |
| Components | shadcn/ui (`radix-nova` preset) |
| Icons | animate-ui icon registry (Motion + Lucide) |
| Loading | `thinking-orbs` |
| Toasts | sonner |
| Theme | `next-themes` |

## Running it

The API must be running on port 8000 (see the root README). Vite proxies
`/api`, `/health`, and `/docs` to it, so the SPA stays same-origin in dev and
the httpOnly refresh cookie is sent without any SameSite or CORS caveats.

```powershell
cd frontend
npm install
npm run dev
```

| Script | Purpose |
|---|---|
| `npm run dev` | Dev server on :5173 with HMR |
| `npm run build` | Typecheck (`tsc -b`) then production build |
| `npm run preview` | Serve the built output |
| `npm run lint` | oxlint |

> On Windows, run npm through `cmd /c` (e.g. `cmd /c "npm run dev"`) if a
> script's flags get mangled by the PowerShell `npm.ps1` wrapper.

## Auth model

The backend issues a short-lived JWT **in the response body** and a rotating
refresh token in an **httpOnly cookie**. This app mirrors that split:

- The access token lives in a **module-scoped variable**, not `localStorage`.
  A JWT in memory cannot be read by a script that survives a page load, and the
  refresh cookie is the only credential that persists.
- On boot, `AuthProvider` calls `POST /auth/refresh` to re-establish the session
  from the cookie. Route guards wait for that to settle before redirecting —
  otherwise a signed-in user would be bounced to `/login` on every hard refresh.
- Concurrent `401`s share **one** in-flight refresh (`refreshSession` in
  `lib/api.ts`). The backend rotates refresh tokens and treats a replayed one as
  theft, revoking the whole family — so parallel requests must not each try to
  refresh.

## Layout

```
src/
├── lib/
│   ├── api.ts           fetch wrapper, single-flight refresh, ApiError
│   ├── endpoints.ts     one typed function per backend route
│   ├── types.ts         mirrors backend/app/schemas/
│   ├── format.ts        UTC formatting, money, day names, overlap check
│   ├── auth-context.ts  context + useAuth
│   └── utils.ts         cn() re-export
├── hooks/
│   ├── use-auth.tsx     AuthProvider
│   └── use-async.ts     useAsync / useMutation / useDebounced / useNow
├── components/
│   ├── animate-ui/icons  (registry — do not hand-edit)
│   ├── ui/               (shadcn registry — do not hand-edit)
│   ├── orb-loader.tsx    all loading states
│   └── ...               app shell, cards, badges, feedback
└── routes/               one file per screen, lazily loaded
```

## Conventions worth knowing

**Money is a string.** Pydantic v2 serialises `Decimal` to a JSON string, so
`price_per_hour` arrives as `"800.00"`. Every monetary field is typed `Money`
(`string | number`) and must pass through `toAmount()` before arithmetic.

**All times are UTC.** The availability endpoint takes `date=YYYY-MM-DD`
interpreted as UTC midnight and generates slots inside that day. Formatting
those in the viewer's local zone would show a 14:00 UTC slot as 19:30 and
contradict the date the user picked, so `format.ts` pins every formatter to UTC.

**Loading states are orbs, not spinners.** `components/orb-loader.tsx` maps each
orb's animation to the verb the app is actually performing — `connecting` while
the session restores, `searching` for list fetches, `breathing` for an empty
day. The orbs are monochrome and follow the theme automatically because
`next-themes` writes the `dark` class that `theme="auto"` watches for.

**Icon substitutions.** The animate-ui registry has no `calendar`, `mail`,
`pencil`, or `shield`. Rather than mix icon libraries, the app substitutes
semantically close icons: `Clock` for dates, `Lock`/`LockKeyholeOpen` for the
password reveal toggle, `SlidersHorizontal` for edit/manage, `MessageCircleWarning`
for alerts, `Lightbulb` for inline hints.

**Route-level code splitting.** Screens are `lazy()`-loaded, so a customer never
downloads the admin or owner surfaces. This also gives the orbs a job on route
transitions via the `Suspense` fallback.

**Overlap is checked client-side too.** `findOverlappingWindow` in `format.ts`
mirrors the `no_overlapping_schedules` exclusion constraint (half-open
intervals) so the schedule editor can explain a clash instead of surfacing a
bare 409. The database stays the authority.

## Registry commands

```powershell
# shadcn components
cmd /c "npx shadcn@latest add dialog table --yes"

# animate-ui icons (name must exist in their registry)
cmd /c "npx shadcn@latest add @animate-ui/icons-search --yes"
```

After adding icons, run the post-processor. The registry emits an unused
`import * as React` and a value import of Motion's `Variants` type, both of
which are errors under this project's `verbatimModuleSyntax` and
`noUnusedLocals` settings:

```powershell
node scripts/fix-animate-ui-icons.mjs
```

`components/ui/` and `components/animate-ui/` are excluded from oxlint in
`.oxlintrc.json` — they are vendored registry output, not project code.
