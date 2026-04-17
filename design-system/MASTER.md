# Support2Thrive Design System — MASTER

> Source of Truth for all UI decisions on the Support2Thrive platform.
> Style: **Accessible & Ethical** (UI/UX Pro Max) blended with warmth for community feel.
> Generated: 2026-04-13 | Stack: Django templates + HTMX + Tailwind CSS (CDN)

---

## Colour Tokens

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `primary` | `#1E40AF` | `blue-800` | Nav, headings, primary buttons, links |
| `primary-light` | `#3B82F6` | `blue-500` | Hover states, secondary links, badges |
| `primary-pale` | `#DBEAFE` | `blue-100` | Tag backgrounds, subtle highlights |
| `cta` / `warm` | `#F59E0B` | `amber-500` | CTA buttons, warm accents, focus rings, urgent items |
| `cta-hover` | `#D97706` | `amber-600` | CTA button hover |
| `success` | `#22C55E` | `green-500` | Positive actions, referral complete, status badges |
| `success-pale` | `#DCFCE7` | `green-100` | Success badge backgrounds |
| `danger` | `#EF4444` | `red-500` | Errors, destructive actions |
| `danger-pale` | `#FEE2E2` | `red-100` | Error badge backgrounds |
| `bg-page` | `#FAFAF8` | custom | Page background — warm white, not cold gray |
| `bg-surface` | `#FFFFFF` | `white` | Cards, panels, modals |
| `text-primary` | `#1E3A8A` | `blue-950` | Body text — high contrast on white |
| `text-muted` | `#475569` | `slate-600` | Secondary text — passes WCAG AA |
| `text-inverse` | `#FFFFFF` | `white` | Text on dark/coloured backgrounds |
| `border` | `#E2E8F0` | `slate-200` | Card borders, dividers |

### Anti-patterns
- Never use `gray-400` or lighter for body text (fails contrast)
- Never use `primary-100` background with `primary-600` text (may fail WCAG AA)
- No neon colours, no AI purple/pink gradients
- No `bg-gray-50` — use `bg-[#FAFAF8]` for the warm page background

---

## Typography

| Role | Font | Weight | Tailwind Class |
|---|---|---|---|
| Display / Hero | Figtree | 700 | `font-heading text-4xl font-bold` |
| Page heading (H1) | Figtree | 700 | `font-heading text-3xl font-bold` |
| Section heading (H2) | Figtree | 600 | `font-heading text-2xl font-semibold` |
| Sub-heading (H3) | Figtree | 600 | `font-heading text-xl font-semibold` |
| Body | Noto Sans | 400 | `font-body text-base leading-relaxed` |
| Body strong | Noto Sans | 600 | `font-body text-base font-semibold` |
| Small / Caption | Noto Sans | 400 | `font-body text-sm text-slate-600` |
| Nav / Label | Noto Sans | 500 | `font-body text-sm font-medium` |

### Google Fonts Import
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&family=Noto+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

### Tailwind fontFamily config
```js
fontFamily: {
  heading: ['Figtree', 'system-ui', 'sans-serif'],
  body: ['Noto Sans', 'system-ui', 'sans-serif'],
},
```

---

## Spacing & Layout

| Token | Value | Notes |
|---|---|---|
| Container max-width | `max-w-7xl` | Standard content width |
| Container narrow | `max-w-3xl` | Forms, articles |
| Container medium | `max-w-5xl` | Lists, cards |
| Horizontal padding | `px-4 sm:px-6 lg:px-8` | Always responsive |
| Section vertical gap | `py-12 md:py-16` | Between major sections |
| Card gap | `gap-6` | Grid/flex card spacing |
| Component padding | `p-6` | Inside cards |

---

## Border Radius (Standardised)

| Element | Class |
|---|---|
| Cards, panels | `rounded-xl` |
| Buttons, inputs, badges | `rounded-lg` |
| Avatars, circular elements | `rounded-full` |
| Tags, small badges | `rounded-md` |

---

## Shadows

| Usage | Class |
|---|---|
| Default card | `shadow-sm` |
| Elevated card / dropdown | `shadow-md` |
| Modal / overlay | `shadow-xl` |
| No shadow (bordered card) | `border border-slate-200` |

---

## Components

### Primary Button
```html
<button class="inline-flex items-center justify-center rounded-lg bg-blue-800 px-4 py-2.5 min-h-[44px] text-sm font-medium text-white transition-colors duration-200 hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 cursor-pointer">
  Button text
</button>
```

### CTA Button (warm amber)
```html
<a class="inline-flex items-center justify-center rounded-lg bg-amber-500 px-6 py-3 min-h-[44px] text-sm font-semibold text-white transition-colors duration-200 hover:bg-amber-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 cursor-pointer">
  Call to action
</a>
```

### Secondary / Ghost Button
```html
<button class="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white px-4 py-2.5 min-h-[44px] text-sm font-medium text-blue-800 transition-colors duration-200 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 cursor-pointer">
  Secondary
</button>
```

### Card
```html
<div class="rounded-xl bg-white shadow-sm border border-slate-200 p-6">
  <!-- content -->
</div>
```

### Clickable Card (with hover)
```html
<a class="block rounded-xl bg-white shadow-sm border border-slate-200 p-6 transition-colors duration-200 hover:border-blue-300 hover:shadow-md cursor-pointer">
  <!-- content -->
</a>
```

### Status Badge
```html
<!-- success -->
<span class="inline-flex items-center rounded-md bg-green-100 px-2 py-1 text-xs font-medium text-green-800" aria-label="Status: Active">Active</span>
<!-- warning -->
<span class="inline-flex items-center rounded-md bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800" aria-label="Status: Pending">Pending</span>
<!-- danger -->
<span class="inline-flex items-center rounded-md bg-red-100 px-2 py-1 text-xs font-medium text-red-800" aria-label="Status: Error">Error</span>
```

---

## Icons

**Rule: No emojis as icons.** Use inline Heroicons SVGs only.

```html
<!-- Always: aria-hidden="true" on decorative icons -->
<svg class="w-5 h-5 text-blue-800" aria-hidden="true" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
  <!-- path here -->
</svg>

<!-- Semantic icons (icon-only buttons): add aria-label to the button, not the SVG -->
<button aria-label="Delete event" class="...">
  <svg class="w-5 h-5" aria-hidden="true" ...>...</svg>
</button>
```

Heroicons source: https://heroicons.com (use outline style, stroke-width="2")

---

## Focus & Accessibility

| Rule | Implementation |
|---|---|
| Focus ring | `focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500` |
| Touch targets | `min-h-[44px] min-w-[44px]` on all interactive elements |
| Colour contrast | Text: 4.5:1 minimum (WCAG AA); large text: 3:1 |
| Reduced motion | Wrap animations in `@media (prefers-reduced-motion: no-preference)` |
| Skip link | `<a href="#main-content" class="sr-only focus:not-sr-only">Skip to content</a>` |
| Form labels | Always use `<label for="...">`, never placeholder-only |
| Fieldsets | Group radio/checkbox with `<fieldset>` + `<legend>` |
| Error linking | Use `aria-describedby` to link errors to their field |

---

## Animation

| Context | Duration | Easing |
|---|---|---|
| Colour/border transitions | `duration-200` | `ease-in-out` |
| Shadow transitions | `duration-200` | `ease-in-out` |
| Page-level transitions | Avoid — use HTMX swap only | — |
| Loading states | Skeleton screens preferred over spinners | — |

---

## RTL Support

The platform supports Arabic (ar) and Urdu (ur) which are RTL languages.

```html
<!-- base.html sets dir on <html> -->
<html lang="{{ LANGUAGE_CODE }}" dir="{% if LANGUAGE_CODE == 'ar' or LANGUAGE_CODE == 'ur' %}rtl{% else %}ltr{% endif %}">
```

- Use `ms-` / `me-` (margin-start/end) instead of `ml-` / `mr-` where RTL matters
- Test all new templates in RTL mode

---

## Page-Level Overrides

Page-specific deviations from this master live in `design-system/pages/<page>.md`.
When building a specific page, check that file first — its rules override this master.

Current page overrides:
- `design-system/pages/pathways.md` — Phase 5 pathway pages
