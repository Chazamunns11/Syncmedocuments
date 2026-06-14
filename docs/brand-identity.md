# Tendari — Brand Identity

The visual identity for Tendari, the coach-first CRM. See `docs/branding.md` for how the *name* was
chosen and `docs/business-plan.md` for positioning.

---

## Logo
- **Concept:** a single continuous line forming a sprouting tendril that curves up and coils — growth +
  a nurturing connection ("tending your client garden / your follow-ups, tended for you").
- **Official artwork:** the generated PNG logo (forest-green single-line sprout above the "Tendari"
  wordmark on an off-white field). **Drop the original file at `tendari/public/brand/logo.png`** to use
  it directly — the app references a brand logo from `/brand/`.
- **Vector interpretation (committed):** `tendari/public/brand/logo.svg` (mark + wordmark) and
  `logo-mark.svg` (icon only) — clean, scalable, recolorable versions aligned to the concept. Swap in the
  PNG or a professionally redrawn SVG when ready.
- **Clear space:** keep padding ≥ the height of the "T" around the logo. **Min size:** icon 24px,
  full lockup 120px wide.
- **Don'ts:** don't add gradients/shadows, don't recolor outside the palette, don't stretch, don't place
  the green mark on a busy or low-contrast background.

## Colour palette
| Token | Hex | Use |
|---|---|---|
| **Forest (primary)** | `#1F6B4C` | logo mark, primary buttons, key accents |
| **Deep green (ink-green)** | `#134E37` | headings, wordmark, dark UI text on light |
| **Sage** | `#8FB7A3` | secondary accents, hovers, illustrations |
| **Mint (tint)** | `#E4EFE7` | section backgrounds, cards, badges |
| **Off-white (canvas)** | `#F2F4EC` | page background (matches the logo field) |
| **Ink** | `#14281F` | body text |
| **Muted** | `#5B6B61` | secondary text |

These are wired into the app as CSS variables / Tailwind theme tokens (see `tendari/app/globals.css`
and `tailwind.config.ts`).

## Typography
- **Headings & wordmark:** a friendly geometric sans — **Poppins** or **Nunito** (rounded, warm, premium).
- **Body/UI:** a clean neutral sans (Inter, or the system stack) for readability.
- The app currently ships with a system rounded stack to avoid build-time font fetches; swap to Poppins
  via `next/font` when convenient.

## Voice & tone
Warm, plain-spoken, confident, anti-jargon. We speak to a busy solo coach, not an agency. Short
sentences. Benefit-first. No hype, no bro-marketing. Promises we keep: *no bill shock, own your data,
set up in a day.*

## Higgsfield logo prompts (for regenerating/variations)
**Primary (icon):**
```
Minimalist flat vector logo for "Tendari", a warm premium software brand for coaches.
A single continuous line forming a small sprouting plant tendril that curves upward and
gently coils at the tip, suggesting growth and a nurturing connection. Clean geometric
line-art icon, balanced negative space, rounded soft terminals, modern and approachable.
Deep forest green (#1F6B4C) with a soft sage accent, on a clean off-white background.
Centered, simple, scalable app-icon style, no text, no gradients, no 3D, no shadows.
```
**Negative prompt:** `photorealistic, 3D, gradients, drop shadow, clutter, busy detail, watermark,
text errors, extra letters`. Set text in a real font (Poppins) rather than trusting the model to spell.
