import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#4F46E5', // Indigo 600
        'primary-dark': '#4338CA', // Indigo 700
        secondary: '#10B981', // Emerald 500
        danger: '#EF4444', // Red 500
        success: '#22C55E', // Green 500
        warning: '#F59E0B', // Amber 500
        info: '#3B82F6', // Blue 500
        background: '#F9FAFB', // Gray 50
        text: '#1F2937', // Gray 900
        'text-light': '#6B7280', // Gray 500
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        'custom-light': '0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03)',
        'custom-medium': '0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06)',
      },
    },
  },
  plugins: [],
} satisfies Config;