---
name: Enterprise Observability System
colors:
  surface: '#0e150e'
  surface-dim: '#0e150e'
  surface-bright: '#343b33'
  surface-container-lowest: '#091009'
  surface-container-low: '#171d16'
  surface-container: '#1b211a'
  surface-container-high: '#252c24'
  surface-container-highest: '#30372e'
  on-surface: '#dde5d8'
  on-surface-variant: '#bdcab9'
  inverse-surface: '#dde5d8'
  inverse-on-surface: '#2b322a'
  outline: '#879484'
  outline-variant: '#3e4a3c'
  surface-tint: '#64df74'
  primary: '#82fd8e'
  on-primary: '#003910'
  primary-container: '#65e075'
  on-primary-container: '#006120'
  inverse-primary: '#006e26'
  secondary: '#aac7ff'
  on-secondary: '#003064'
  secondary-container: '#3e90ff'
  on-secondary-container: '#002957'
  tertiary: '#ffdccd'
  on-tertiary: '#50240b'
  tertiary-container: '#ffb794'
  on-tertiary-container: '#7a462a'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#81fc8d'
  primary-fixed-dim: '#64df74'
  on-primary-fixed: '#002106'
  on-primary-fixed-variant: '#00531a'
  secondary-fixed: '#d6e3ff'
  secondary-fixed-dim: '#aac7ff'
  on-secondary-fixed: '#001b3e'
  on-secondary-fixed-variant: '#00468d'
  tertiary-fixed: '#ffdbcb'
  tertiary-fixed-dim: '#feb693'
  on-tertiary-fixed: '#341100'
  on-tertiary-fixed-variant: '#6b3a1f'
  background: '#0e150e'
  on-background: '#dde5d8'
  surface-variant: '#30372e'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  metric-lg:
    fontFamily: JetBrains Mono
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 32px
  metric-md:
    fontFamily: JetBrains Mono
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 20px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 16px
  margin: 24px
---

## Brand & Style

The design system is engineered for high-stakes AI production monitoring. It prioritizes **data density, technical precision, and rapid cognition**. The brand personality is authoritative and systematic, designed for Site Reliability Engineers (SREs) and AI Platform teams who require a "single pane of glass" for complex LLM telemetry.

The visual style is a refined **Corporate Modern** aesthetic tailored for dark-mode environments. It utilizes a layered tonal approach where depth is communicated through color shifts rather than shadows, ensuring that the focus remains entirely on data visualization and system health metrics. The interface feels like a high-performance tool: lean, efficient, and devoid of unnecessary ornamentation.

## Colors

The color palette is optimized for long-duration monitoring in low-light environments. The foundation is built on **Splunk Dark**, utilizing three distinct levels of gray to establish visual hierarchy:
- **Background**: The base layer for the application shell.
- **Surface**: Used for sidebars, navigation headers, and secondary grouping.
- **Card**: The highest contrast surface for content modules and data widgets.

**Brand Green** is used sparingly for primary actions and brand presence. The **Semantic Status Palette** (Success, Warning, Error) follows industry-standard observability conventions to ensure that system degradation is immediately identifiable even at a glance.

## Typography

This design system employs a dual-font strategy to balance readability with technical utility. 

**Inter** is the primary typeface for all UI controls, headers, and descriptive text. Its neutral, high-legibility design ensures that the interface remains unobtrusive.

**JetBrains Mono** is utilized for all data-driven content, including metrics, timestamps, UUIDs, and SPL (Splunk Processing Language) queries. The monospaced nature of the font ensures that numerical values align perfectly in tables and dashboards, allowing users to scan for changes in magnitude across large datasets efficiently.

- **Headlines**: Use semibold weights with tight tracking for a compact, professional feel.
- **Body**: Standardized at 14px for the majority of the UI to maximize information density.
- **Metrics**: Always monospaced to prevent "jumping" during real-time data updates.

## Layout & Spacing

The layout philosophy is a **Structured Fluid Grid** optimized for 1440px+ monitors but responsive down to tablet sizes. It uses an **8px base unit** (with 4px increments for tight components) to maintain a rigorous mathematical rhythm.

### Grid & Composition
- **Desktop**: 12-column grid with 16px gutters. Widgets typically span 3, 4, 6, or 12 columns.
- **Density**: High density is preferred. Padding inside cards is restricted to 16px to maximize the data visualization area.
- **Alignment**: All data charts and table headers must align to the vertical grid lines.

### Responsive Behavior
- **Tablet**: Columns collapse to 6; sidebars become collapsible icons.
- **Mobile**: Single-column vertical stack; data tables convert to scrollable lists or simplified cards.

## Elevation & Depth

In this design system, depth is achieved through **Tonal Layering** and **Structural Outlines** rather than traditional shadows. This ensures the UI remains crisp and high-contrast, which is critical for legibility in dense dashboards.

- **Base Layer**: Background (`#0B0D12`).
- **Mid Layer**: Surface (`#151820`). Used for navigation and persistent panels.
- **Top Layer**: Card (`#1C2030`). Used for individual metric widgets and interactive modules.
- **Borders**: Every interactive element or container is defined by a 1px solid border (`#2A3347`). 
- **Active State**: Use a subtle 1px Brand Green border or a Neutral Blue glow to indicate focus/active selection. Shadows are only permitted for floating menus or modals, using a sharp, low-spread dark shadow.

## Shapes

The design system uses a **Soft** shape language. This provides a professional, modern feel without appearing overly "consumer-focused" or "playful."

- **Components**: Buttons, inputs, and small widgets use a **0.25rem (4px)** corner radius.
- **Containers**: Cards and large modules use a **0.5rem (8px)** corner radius.
- **Status Indicators**: Status dots and "pill" badges for health states are fully rounded (pill-shaped) to distinguish them from structural UI elements.

## Components

### Buttons & Inputs
- **Primary Button**: Brand Green background with dark text. 1px border.
- **Ghost Button**: Transparent background with 1px border. Secondary text color.
- **Input Fields**: Card-colored background with 1px border. Focus state changes border to Primary Green.

### Data Tables
- **Header**: Surface-colored background, semibold text, all-caps labels.
- **Cells**: 12px monospaced text for data. 1px bottom border only.
- **Striping**: Use a subtle background shift on alternate rows for high-row-count readability.

### Status Indicators
- **Badges**: Small, high-contrast badges using the Semantic Status Palette. 
- **Health Dots**: 8px circles positioned next to service names. Use a "pulsing" animation only for Error states.

### Visualization Widgets
- **Gauges**: High-contrast strokes (2px) against the card background.
- **Sparklines**: Simplified charts with no axes, used inside table cells to show 24h trends.
- **Logs**: Dark monospace blocks using `#0B0D12` backgrounds within cards to simulate a terminal environment.