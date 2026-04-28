/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      colors: {
        // Map Material Design tokens to Tailwind color utilities
        // These consume Angular Material's CSS variables
        primary: {
          DEFAULT: 'var(--mat-sys-primary)',
          container: 'var(--mat-sys-primary-container)',
          fixed: 'var(--mat-sys-primary-fixed)',
          'fixed-dim': 'var(--mat-sys-primary-fixed-dim)',
        },
        secondary: {
          DEFAULT: 'var(--mat-sys-secondary)',
          container: 'var(--mat-sys-secondary-container)',
          fixed: 'var(--mat-sys-secondary-fixed)',
          'fixed-dim': 'var(--mat-sys-secondary-fixed-dim)',
        },
        tertiary: {
          DEFAULT: 'var(--mat-sys-tertiary)',
          container: 'var(--mat-sys-tertiary-container)',
          fixed: 'var(--mat-sys-tertiary-fixed)',
          'fixed-dim': 'var(--mat-sys-tertiary-fixed-dim)',
        },
        error: {
          DEFAULT: 'var(--mat-sys-error)',
          container: 'var(--mat-sys-error-container)',
        },
        surface: {
          DEFAULT: 'var(--mat-sys-surface)',
          dim: 'var(--mat-sys-surface-dim)',
          bright: 'var(--mat-sys-surface-bright)',
          container: {
            DEFAULT: 'var(--mat-sys-surface-container)',
            low: 'var(--mat-sys-surface-container-low)',
            lowest: 'var(--mat-sys-surface-container-lowest)',
            high: 'var(--mat-sys-surface-container-high)',
            highest: 'var(--mat-sys-surface-container-highest)',
          },
        },
        outline: {
          DEFAULT: 'var(--mat-sys-outline)',
          variant: 'var(--mat-sys-outline-variant)',
        },
      },
      // Material Design spacing scale (4px base unit)
      spacing: {
        'mat-0': '0',
        'mat-1': '4px',
        'mat-2': '8px',
        'mat-3': '12px',
        'mat-4': '16px',
        'mat-5': '20px',
        'mat-6': '24px',
        'mat-8': '32px',
        'mat-10': '40px',
        'mat-12': '48px',
        'mat-16': '64px',
        'mat-20': '80px',
        'mat-24': '96px',
      },
      // Material Design elevation shadows
      boxShadow: {
        'mat-elevation-1': 'var(--mat-sys-level1)',
        'mat-elevation-2': 'var(--mat-sys-level2)',
        'mat-elevation-3': 'var(--mat-sys-level3)',
        'mat-elevation-4': 'var(--mat-sys-level4)',
        'mat-elevation-5': 'var(--mat-sys-level5)',
      },
      // Material Design typography scale
      fontSize: {
        'display-large': ['57px', { lineHeight: '64px', fontWeight: '400' }],
        'display-medium': ['45px', { lineHeight: '52px', fontWeight: '400' }],
        'display-small': ['36px', { lineHeight: '44px', fontWeight: '400' }],
        'headline-large': ['32px', { lineHeight: '40px', fontWeight: '400' }],
        'headline-medium': ['28px', { lineHeight: '36px', fontWeight: '400' }],
        'headline-small': ['24px', { lineHeight: '32px', fontWeight: '400' }],
        'title-large': ['22px', { lineHeight: '28px', fontWeight: '400' }],
        'title-medium': ['16px', { lineHeight: '24px', fontWeight: '500' }],
        'title-small': ['14px', { lineHeight: '20px', fontWeight: '500' }],
        'body-large': ['16px', { lineHeight: '24px', fontWeight: '400' }],
        'body-medium': ['14px', { lineHeight: '20px', fontWeight: '400' }],
        'body-small': ['12px', { lineHeight: '16px', fontWeight: '400' }],
        'label-large': ['14px', { lineHeight: '20px', fontWeight: '500' }],
        'label-medium': ['12px', { lineHeight: '16px', fontWeight: '500' }],
        'label-small': ['11px', { lineHeight: '16px', fontWeight: '500' }],
      },
      // Material Design border radius scale
      borderRadius: {
        'mat-none': '0',
        'mat-xs': '4px',
        'mat-sm': '8px',
        'mat-md': '12px',
        'mat-lg': '16px',
        'mat-xl': '28px',
        'mat-full': '9999px',
      },
    },
  },
  plugins: [],
  // Respect user's prefers-reduced-motion setting
  corePlugins: {
    // Disable preflight to avoid conflicts with Material's base styles
    preflight: false,
  },
};
