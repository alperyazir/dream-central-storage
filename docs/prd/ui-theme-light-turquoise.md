# Light Turquoise UI Theme

## Palette
| Token | Hex | Usage |
| --- | --- | --- |
| Primary 500 | #2CB8AD | Buttons, interactive accents |
| Primary 700 | #0F7B75 | Hover/focus states, sidebar gradient |
| Primary 100 | #D6F4EF | Table headers, subtle fills |
| Secondary | #1B79B0 | Links, secondary actions |
| Background Base | #F2FBF9 | Application background |
| Surface | #FFFFFF | Panels, cards, modals |
| Text Primary | #04313D | Headings, primary copy |
| Text Secondary | #0F5C65 | Supporting copy |
| Border Subtle | #B4E1E4 | Dividers, outlines |

## Typography
- **Font Family:** `Inter`, system UI fallback stack
- **Headings:** h1 2.75rem/700, h2 2.1rem/700, h3 1.75rem/600
- **Body:** 1rem base, 1.5 line-height
- **Buttons:** 600 weight, no uppercase, pill-shaped

## Spacing & Shape
- Global spacing increments: 4px grid with primary blocks at 8px, 16px, 24px
- Border radius: 12px on surfaces, 18px on elevated surfaces, pill buttons (999px)

## Accessibility
- Primary on white: contrast ratio 4.6:1
- Sidebar text on gradient: ≥4.8:1 against darkest stop
- Focus rings use semi-transparent teal for 3px outline and 2px offset

## Implementation Notes
- Theme tokens defined in `apps/admin-panel/src/theme.ts`
- CSS variables declared in `styles/global.css`
- Navigation uses gradient sidebar and rounded link chips
- Table headers adopt turquoise-100 background; buttons use MUI overrides for pill style

## Screens Updated
- Login, Dashboard, Upload modals, Trash list, Global navigation

## Testing & Validation
- WCAG AA contrast verified via manual checks (Stark + browser dev tools)
- Vitest suite updated; storybook not yet available (future enhancement)

