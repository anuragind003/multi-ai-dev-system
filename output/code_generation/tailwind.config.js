/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#4F46E5', // Indigo-600
        secondary: '#6B7280', // Gray-500
        accent: '#EC4899', // Pink-500
        background: '#F9FAFB', // Gray-50
        text: '#1F2937', // Gray-900
        'text-light': '#4B5563', // Gray-600
        success: '#10B981', // Green-500
        error: '#EF4444', // Red-500
        warning: '#F59E0B', // Amber-500
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        'soft': '0 4px 6px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.02)',
        'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
      },
    },
  },
  plugins: [],
}