# Frontend Accessibility Baseline

The dashboard frontend follows an accessibility baseline suitable for the current
prototype and pilot stages.

## Implemented

- Skip navigation link to the primary content landmark.
- Semantic status and alert announcements for API state and errors.
- Explicit labels and accessible names for all prediction inputs.
- Keyboard-visible focus indicators.
- WAI-ARIA tablist, tab, and tabpanel semantics for diagnostic sections.
- Loading state exposed through `aria-busy`, with actions disabled while a
  prediction is being submitted.
- Responsive horizontal scrolling for diagnostic tabs on narrow screens.
- Reduced-motion support through `prefers-reduced-motion`.
- Decorative status indicators hidden from assistive technology.

## Validation

Run the frontend checks from `frontend/`:

```powershell
npm run lint
npm run build
```

The current lint baseline has one existing React Hook dependency warning for the
initial automatic analysis callback. It does not produce a lint error or block
the production build. The Vite bundle-size warning is tracked separately as a
performance optimization item.

## Remaining production work

Before institutional rollout, validate the deployed UI with keyboard-only
navigation, a screen reader, browser zoom at 200%, high-contrast settings, and
automated accessibility tooling such as axe. The frontend should also add
automated component tests for tab keyboard interaction and error announcements.
