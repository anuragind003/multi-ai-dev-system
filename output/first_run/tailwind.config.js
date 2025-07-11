/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'primary': '#3498db', // Example primary color
        'secondary': '#2ecc71', // Example secondary color
        'dark': '#2c3e50', // Example dark color
        'light': '#ecf0f1', // Example light color
      },
    },
  },
  plugins: [],
}