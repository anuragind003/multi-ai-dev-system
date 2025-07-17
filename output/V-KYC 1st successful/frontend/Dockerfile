# Stage 1: Build the Next.js application
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package.json and yarn.lock (or package-lock.json) to leverage Docker cache
COPY package.json yarn.lock* ./

# Install dependencies
# Using `ci` for clean installs in CI/CD environments
RUN yarn install --frozen-lockfile

# Copy the rest of the application code
COPY . .

# Build the Next.js application
# `output: "standalone"` creates a self-contained output that includes a custom server.js
# This is ideal for Docker as it minimizes the final image size.
RUN yarn build

# Stage 2: Run the Next.js application in a minimal environment
FROM node:18-alpine AS runner

# Set working directory
WORKDIR /app

# Create a non-root user for security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy the standalone output from the builder stage
# This includes the .next folder, public folder, and the standalone server.js
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# Set environment variables for Next.js production
ENV NODE_ENV production
ENV PORT 3000

# Expose the port the application will run on
EXPOSE 3000

# Switch to the non-root user
USER nextjs

# Command to run the Next.js application
# The standalone output generates a server.js that can be run directly
CMD ["node", "server.js"]