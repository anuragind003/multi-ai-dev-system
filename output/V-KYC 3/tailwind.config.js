/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#4F46E5', // Indigo 600
        'primary-dark': '#4338CA', // Indigo 700
        secondary: '#10B981', // Emerald 500
        'secondary-dark': '#059669', // Emerald 600
        danger: '#EF4444', // Red 500
        success: '#22C55E', // Green 500
        warning: '#F59E0B', // Amber 500
        info: '#3B82F6', // Blue 500
        background: '#F9FAFB', // Gray 50
        text: '#1F2937', // Gray 900
        'text-light': '#6B7280', // Gray 500
        border: '#E5E7EB', // Gray 200
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'modal': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
      },
    },
  },
  plugins: [],
}