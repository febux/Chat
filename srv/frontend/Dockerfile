# Stage 1: Build the React (Vite) Application
FROM node:24-alpine AS builder

WORKDIR /app
# Copy the package.json and install dependencies
COPY ./src/frontend/package.json .
# Use a cache layer for dependencies to improve build speed
RUN --mount=type=cache,target=/root/.npm npm install
# Copy the rest of the source code to the container
RUN --mount=type=cache,target=/root/.npm npm ci
# Run the build script to generate the production build
RUN npm i -g serve
# Copy source code to the container
COPY ./src/frontend .
# Build the production build (this is done in a separate stage to reduce the size of the final image)
# This is necessary because the build dependencies are not included in the final image,
RUN npm run build

# Stage 2: Serve static files with Node.js + `serve`
FROM node:24-alpine AS runner
# Set the environment to production for smaller + optimized installs
ENV NODE_ENV=production
# Set the working directory inside the container
WORKDIR /app
# Copy only the production build output from the builder stage
COPY --link --from=builder /app/dist ./dist
# Install only the `serve` package (no global install, pinned version)
RUN --mount=type=cache,target=/root/.npm npm install serve@^14.2.6 --omit=dev
# Run the container as a non-root user for security best practices
USER node
# Expose port 3000 (the same port configured in "serve -l 3000")
EXPOSE 3000
# Run `serve` directly to serve the built app
CMD ["npx", "serve", "-s", "dist", "-l", "3000"]

# Build Stage
FROM node:24-alpine AS build
WORKDIR /app
COPY ./src/frontend/package.json .
RUN npm install
COPY ./src/frontend .
RUN npm run build

# Production Stage
FROM nginx:latest AS production

RUN rm /etc/nginx/conf.d/default.conf
COPY ./config/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
