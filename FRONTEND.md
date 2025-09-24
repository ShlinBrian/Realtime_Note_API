# Design Tokens & UI Rules

This document defines the design system and UI consistency rules for the Realtime Notes frontend.

## Current Implementation

**Tech Stack**: TypeScript + Vanilla DOM + CSS (inline styles)
**Styling Approach**: CSS-in-HTML with CSS custom properties and consistent design tokens

## Design Tokens

### Typography Scale
- **12px**: Small text, labels, metadata (`font-size: 12px`)
- **14px**: Body text, form inputs (`font-size: 14px`)
- **16px**: Primary content, note titles (`font-size: 16px`)
- **18px**: Header text, page titles (`font-size: 18px`)
- **20px**: Large headers
- **24px**: Section headings
- **30px**: Page headers
- **36px**: Hero text

### Spacing Scale
- **4px**: Minimal spacing, borders
- **8px**: Small gaps, padding
- **12px**: Standard padding, form spacing
- **16px**: Section padding, card spacing
- **20px**: Page padding, content spacing
- **24px**: Large content gaps
- **32px**: Section separation

### Border Radius
- **4px**: Small elements (buttons, inputs)
- **6px**: Cards, containers
- **8px**: Large containers
- **50%**: Circular elements (avatars, status indicators)

### Shadows & Elevation
- **Light**: `0 2px 4px rgba(0, 0, 0, 0.1)` - Headers, subtle elevation
- **Medium**: `0 4px 8px rgba(0, 0, 0, 0.15)` - Cards, modals
- **Heavy**: `0 8px 16px rgba(0, 0, 0, 0.2)` - Dropdowns, overlays

### Colors

#### Brand Colors
- **Primary**: `#61dafb` - Links, accents, focus states
- **Primary Hover**: `#4fa8c5` - Interactive states

#### Neutral Colors
- **Background**: `#1e1e1e` - Main background
- **Surface**: `#252525` - Sidebar, secondary surfaces
- **Surface Elevated**: `#2d2d2d` - Cards, headers
- **Surface Interactive**: `#3d3d3d` - Hover states
- **Border**: `#404040` - Dividers, input borders
- **Text Primary**: `#e4e4e4` - Main text content
- **Text Secondary**: `#a0a0a0` - Metadata, secondary text
- **Text Muted**: `#6c757d` - Placeholder text, disabled states

#### Status Colors
- **Success**: `#28a745` - Success states, connected status
- **Warning**: `#ffc107` - Warning states, connecting status
- **Error**: `#dc3545` - Error states, disconnected status
- **Info**: `#007acc` - Information, notifications

## Layout System

### Container Rules
- **Main Container**: Full viewport with flex layout
- **Sidebar Width**: `300px` fixed width
- **Content Area**: Flex-grow to fill remaining space
- **Padding**: `16px` for sections, `20px` for main content areas

### Grid & Alignment
- **Flex-based layouts** with consistent gaps
- **Align content** to top-left by default
- **Center alignment** only for empty states and loading states

## Component Patterns

### Cards & Containers
```css
background: #2d2d2d;
border: 1px solid #404040;
border-radius: 4px;
padding: 12px;
```

### Buttons
- **Primary**: Blue background (`#007acc`), white text
- **Secondary**: Gray background (`#6c757d`), white text
- **Danger**: Red background (`#dc3545`), white text
- **Padding**: `8px 16px` standard, `6px 12px` small
- **Border radius**: `4px`
- **Hover**: Darken background by 10-15%

### Form Fields
```css
padding: 8px 12px;
background: #1e1e1e;
border: 1px solid #404040;
border-radius: 4px;
color: #e4e4e4;
```

### Status Indicators
- **Circle**: `8px x 8px`, `border-radius: 50%`
- **Colors**: Success (green), Warning (yellow), Error (red)
- **Animation**: Pulse effect for active states

## Empty/Loading/Error States

### Pattern Structure
```html
<div class="empty-state">
  <i class="icon"></i>
  <p>Descriptive message</p>
  <button>Clear call-to-action</button>
</div>
```

### Styling
- **Center alignment** for empty state containers
- **Icon size**: `48px` with `opacity: 0.5`
- **Text color**: `#6c757d` (muted)
- **Spacing**: `16px` margin between icon and text

## Form Design Rules

### Labels & Inputs
- **Label spacing**: No explicit labels (placeholder-based inputs)
- **Input spacing**: `8px` margin between form fields
- **Error states**: Red border (`#dc3545`) + error text below
- **Error text**: `font-size: 12px`, `color: #dc3545`

### Validation States
- **Default**: Gray border (`#404040`)
- **Focus**: Blue border (`#61dafb`)
- **Error**: Red border (`#dc3545`)
- **Success**: Green border (`#28a745`)

## Animation & Transitions

### Standard Transitions
- **Duration**: `0.2s` for most interactions
- **Easing**: `ease` for general transitions
- **Properties**: `background`, `border-color`, `opacity`, `transform`

### Loading States
- **Pulse animation**: 2s infinite for status indicators
- **Fade transitions**: 0.3s for notifications
- **Slide animations**: 0.3s for dropdowns and modals

## Usage Rules

### Component-First Development
1. **Update core components first** (buttons, inputs, cards)
2. **Page-level code** should only compose existing components
3. **No ad-hoc styling** at the page level - use consistent tokens
4. **Maintain design system** - all new styles should follow these tokens

### Consistency Requirements
- **Use defined spacing scale** - no arbitrary margins/padding
- **Follow color palette** - no inline hex values
- **Maintain typography scale** - consistent font sizes
- **Respect layout patterns** - consistent container and spacing rules

### Future Migration Path
This design system is structured to support future migration to:
- **CSS Custom Properties** for easier token management
- **Component libraries** (React, Vue, etc.)
- **Utility-first frameworks** (Tailwind CSS)
- **Design system tools** (Storybook, Figma tokens)