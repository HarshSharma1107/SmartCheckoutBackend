// =============================================================
// SmartCheckout — Design System
// Single source of truth for the dark theme every screen shares. Was
// previously a COLORS object redeclared (with drift) in every screen file -
// e.g. ScannerScreen.js referenced COLORS.surfaceHigh without ever defining
// it locally, silently surviving only via a `?? "#1C1C27"` fallback.
// =============================================================

export const COLORS = {
  bg:          "#0A0A0F",
  surface:     "#13131A",
  surfaceHigh: "#1C1C27",
  border:      "#2A2A3D",
  accent:      "#00E5A0",
  accentDim:   "#00E5A015",
  text:        "#F0F0F8",
  textMuted:   "#6B6B8A",
  error:       "#FF5370",
  errorDim:    "#FF537015",
  gold:        "#FFB800",
  white:       "#FFFFFF",
  overlay:     "rgba(0,0,0,0.65)",
};

// Named tiers for the radius values already in use across the app.
export const RADIUS = {
  sm:  12,
  md:  14,
  lg:  16,
  xl:  20,
  xxl: 28,
};

export const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
};
