/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  compiler: {
    // Enables the styled-components SWC transform
    // For production, consider removing console.log in production
    // removeConsole: process.env.NODE_ENV === 'production',
  },
  images: {
    domains: ['via.placeholder.com'], // Add any external image domains here
  },
  env: {
    API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:3001/api',
  },
};

module.exports = nextConfig;