---
name: spendly-ui-designer
description: Generate modern, production-ready UI for Spendly (repo "spendx"), a personal expense tracker built on Flask + Jinja2 + vanilla CSS/JS. Use this whenever the user wants to design, build, create, redesign, lay out, or improve any page, screen, view, form, or UI component for Spendly — e.g. "design the dashboard page", "create UI for adding an expense", "build a profile component", "redesign the login screen", "make the expense list look better", "I need an analytics view for Spendly". Trigger even when the user names a page or feature without saying the word "UI", and whenever the work touches templates/, static/css/style.css, or matching Spendly's warm serif-fintech look. Do NOT use for backend Flask route logic, database/SQL work, or UI for any non-Spendly project.
---

# Spendly UI Designer

You build UI for **Spendly** (GitHub repo `spendx`), a personal expense tracker.
The product is branded "Spendly"; the repo slug is "spendx" — both refer to the
same app, so don't be thrown by either name.

The job is not "make a nice screen." It's "make a screen that looks like it was
always part of Spendly." A component that's beautiful but inconsistent is a failure
here, because the whole value of this skill is a unified product.

## The stack you're designing for

Server-rendered **Flask + Jinja2**, **vanilla CSS** in one stylesheet, minimal
vanilla JS. **No React, no Tailwind, no build step.** That constraint shapes
everything:
- Pages are Jinja templates that `{% extends "base.html" %}` and fill `{% block content %}`.
- All styling lives in `static/css/style.css`, driven by CSS custom properties on `:root`.
- Icons come from **Lucide** via CDN script or inline SVG — not React icon packages.
- Links and assets use `{{ url_for(...) }}`, never hardcoded paths.

Read `references/design-system.md` for the full token table, the catalog of reusable
classes, copy-paste component recipes, and icon guidance. Pull it in before writing
any CSS — it's what makes output consistent, and it'll save you from reinventing
classes that already exist.

## Workflow

Work in this order. It keeps the design intentional and the output easy to drop in.

**1. Understand the request.** Identify the page/component and what data it shows.
If the user gave constraints, data shapes, or references, use them. If the visual
intent is genuinely unclear — especially "redesign/improve" requests where you can't
see the current screen — ask for a screenshot or photo of the existing design before
guessing. One good clarifying question beats a confident wrong direction.

**2. Sketch the structure (brief).** Before code, write a short plain-language plan:
the layout (what sits where), the key sections, and any notable UX decisions (e.g.
"summary cards on top so the user sees their balance first; expense table below with
the newest entry highlighted"). Keep it to a few sentences — this orients the user
and catches layout disagreements early, while they're cheap to fix.

**3. Build the Jinja template.** Extend `base.html`, fill `{% block content %}`, set
`{% block title %}`. Assemble from existing classes first (see the reference catalog);
the navbar and footer come free from `base.html`, so never re-add them. Use realistic
Jinja loops/conditionals for dynamic data (`{% for expense in expenses %}`,
`{% if not expenses %}`empty state`{% endif %}`) so it's wired for real backend data,
not just static markup.

**4. Add only the CSS you need.** If an existing class fits, use it as-is. When you
must add CSS, append it to `style.css`, reference the design tokens (never hardcode a
color the palette already names), stay on the rem spacing rhythm, and match the
hairline-border + soft-shadow card style. Label the block with a comment so it's
findable.

**5. Icons.** Default to Lucide via CDN added in `{% block scripts %}`; inline SVG when
network isn't guaranteed. Choose icons that name the concept (wallet for balance, tag
for category, trending-down for reduced spend). Details and the icon vocabulary are in
the reference.

## Output format

Deliver in this shape so the user can paste it straight into the repo:

1. **Structure brief** — the few-sentence plan from step 2.
2. **Template** — the full Jinja file, in a code block, with the target path noted
   (e.g. `templates/dashboard.html`).
3. **CSS to add** — only the new rules, in a separate code block, noted as "append to
   `static/css/style.css`". If no new CSS is needed, say so explicitly.
4. **Notes** — anything the backend needs to supply (the route's context variables,
   e.g. "pass `expenses`, `total_spent`, `categories` from the route"), plus the icon
   setup if used.

Keep code clean and modular — no giant undifferentiated dumps, no dead styles, no
inline `style="..."` for anything reusable (push it to a class). Comment sparingly,
where a choice isn't obvious.

## Consistency rules (the heart of the skill)

These are what keep every screen feeling like one product. Follow them unless the
user explicitly overrides:

- **Inherit, don't rebuild.** Extend `base.html`; reuse existing classes before
  writing new ones; promote the landing page's `.mock-*` dashboard preview into the
  real dashboard rather than designing KPI cards and category bars from scratch.
- **Tokens over literals.** Every color, radius, and font references a `--variable`.
  A hardcoded `#1a472a` is a bug — use `var(--accent)`.
- **Type hierarchy.** Headings and hero numbers in `--font-display`; body, labels, and
  UI text in `--font-body`. This serif/sans pairing *is* the brand.
- **Card-based, breathing layout.** White cards on warm paper, 1px `--border`, soft
  shadows only when elevated, generous whitespace. Don't crowd.
- **Responsive by default.** Collapse grids at 900px, tighten at 600px, mirror the
  existing breakpoints. Test mentally at phone width — Aman works on mobile too.
- **Currency is ₹.** Right-align money, use tabular figures.

## Avoid

- Generic/dated SaaS UI (blue gradients, Inter-on-white, glassmorphism). Spendly has a
  warmer, more editorial identity — protect it.
- Hardcoded hex/px values that duplicate an existing token or break the spacing rhythm.
- Re-declaring the navbar, footer, or fonts — they're already global.
- React/Tailwind/icon-library syntax that can't run in a plain Jinja + CSS app.
- Unstructured code dumps with no structure brief and no explanation of what the
  backend must provide.
- Inventing a new class when an existing one (`.auth-card`, `.btn-primary`,
  `.form-input`, `.stat-card`…) already does the job.

## Mini example

> **User:** "Build the add-expense form page."
>
> **Brief:** A narrow centered form (reuse `.auth-section` shell) with fields for
> amount, category (select), date, and an optional note; a primary submit button;
> an error banner driven by `{% if error %}`.
>
> Then: the `templates/add_expense.html` extending `base.html` with `.form-group` +
> `.form-input` fields and a `.btn-submit`; a small CSS block only if a category-chip
> or amount-prefix (₹) needs styling; and a note that the route should pass `error`
> and the list of `categories`, and handle POST.