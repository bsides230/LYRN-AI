# Stage 1: Builder
# This stage prepares the final web root content by combining the `src` and `public` directories.
FROM alpine:3.18 as builder

# Set the working directory.
WORKDIR /build

# Copy assets from the public directory.
COPY public/ .

# Copy the source files (HTML, CSS, JS) from the src directory.
# This will correctly place index.html at the root of the build,
# and css/styles.css in a css subdirectory.
COPY src/. .


# Stage 2: Final image
# This stage builds the final nginx image that will serve the site.
FROM nginx:1.27-alpine

# Copy our custom Nginx configuration.
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# Copy the prepared web content from the builder stage into the Nginx web root.
COPY --from=builder /build /usr/share/nginx/html
