/** @type {import('tailwindcss').Config} */
const token = name => `rgb(var(--${name}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Archivo', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"Courier Prime"', 'ui-monospace', 'monospace'],
      },
      colors: {
        ground: token('ground'),
        card: { DEFAULT: token('card'), 2: token('card2') },
        ink: { DEFAULT: token('ink'), 2: token('ink2'), 3: token('ink3') },
        rule: { DEFAULT: token('rule'), strong: token('rulestrong') },
        rail: { DEFAULT: token('rail'), 2: token('rail2'), ink: token('railink'), ink2: token('railink2') },
        verm: token('verm'),
        cobalt: token('cobalt'),
        ochre: { DEFAULT: token('ochre'), fill: token('ochrefill') },
        green: token('green'),
        act: { DEFAULT: token('act'), on: token('onact') },
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      transitionTimingFunction: {
        expo: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
      keyframes: {
        'file-in': { from: { transform: 'translateY(8px)' }, to: { transform: 'none' } },
        'rule-run': { from: { transform: 'translateX(-100%)' }, to: { transform: 'translateX(250%)' } },
        'tick': { from: { transform: 'translateY(-60%)', opacity: '0.2' }, to: { transform: 'none', opacity: '1' } },
      },
      animation: {
        'file-in': 'file-in 240ms cubic-bezier(0.16, 1, 0.3, 1)',
        'rule-run': 'rule-run 1.4s cubic-bezier(0.65, 0, 0.35, 1) infinite',
        'tick': 'tick 220ms cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
