/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        surface: {
          950: '#060A13', // app background
          900: '#0B1220', // sidebar / header / panels
          800: '#111A2C', // cards
          700: '#18233B', // raised / hover
          600: '#22304F', // strong borders / tracks
        },
        line: {
          DEFAULT: '#1D2A45', // card borders
          soft: '#141E33',    // subtle dividers
        },
        accent: {
          DEFAULT: '#22D3EE',
          bright: '#67E8F9',
          dim: '#0E7490',
          faint: '#164E63',
        },
        severity: {
          critical: '#ef4444',
          high:     '#f97316',
          medium:   '#eab308',
          low:      '#22c55e',
          info:     '#3b82f6',
        },
      },
      boxShadow: {
        glow: '0 0 24px rgba(34, 211, 238, 0.10)',
        card: '0 1px 3px rgba(0, 0, 0, 0.4)',
      },
      keyframes: {
        'slide-in': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
      },
      animation: {
        'slide-in': 'slide-in 0.25s ease-out',
        'fade-in': 'fade-in 0.3s ease-out',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
