import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4F46E5', // Indigo 600
          dark: '#4338CA',   // Indigo 700
          light: '#6366F1',  // Indigo 500
        },
        secondary: {
          DEFAULT: '#10B981', // Emerald 500
          dark: '#059669',    // Emerald 600
        },
        danger: '#EF4444',    // Red 500
        warning: '#F59E0B',   // Amber 500
        info: '#3B82F6',      // Blue 500
        background: '#F9FAFB', // Gray 50
        text: '#1F2937',      // Gray 900
        'text-light': '#6B7280', // Gray 500
        border: '#E5E7EB',    // Gray 200
      },
      boxShadow: {
        'custom-light': '0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.02)',
        'custom-medium': '0 4px 6px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)',
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
      }
    },
  },
  plugins: [],
};

export default config;