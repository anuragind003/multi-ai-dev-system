# Stage 1: Build the React application
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock)
COPY ./frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY ./frontend/ .

# Build the React app for production
RUN npm run build

# Stage 2: Serve the React application with Nginx
FROM nginx:stable-alpine

# Copy the built React app from the builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Copy custom Nginx configuration
# This configuration will be used by the main Nginx service in docker-compose.prod.yml
# For this specific frontend container, it's just serving static files.
# The main Nginx in docker-compose.prod.yml will handle routing to this container.
COPY ./nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 for Nginx
EXPOSE 80

# Command to run Nginx
CMD ["nginx", "-g", "daemon off;"]