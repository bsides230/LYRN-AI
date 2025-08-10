# LYRN-AI Website

This repository contains the source code for the LYRN-AI static website.

## Project Structure

-   `src/`: Contains the source HTML, CSS, and JavaScript files.
-   `public/`: Contains static assets like images, videos, `robots.txt` and `sitemap.xml`.
-   `nginx/`: Contains the Nginx configuration.
-   `docker/`: Contains the Dockerfile and Docker Compose configuration for deployment.

## How to Run with Docker

The project is configured to run with Docker and Docker Compose, which handles the build process and serves the site.

### Production-like Deployment

To build and run the site from the project root:

```bash
# Build the image and start the container
docker compose -f lyrn-ai-site/docker/docker-compose.yml up -d --build
```

This will:
1.  Build the Docker image using the multi-stage `Dockerfile`. The build process automatically copies the necessary files from both `src` and `public` into the final web server image.
2.  Start the Nginx container.

The site will be running on `http://localhost` (port 80) and `https://localhost` (port 443).

### Local Development

For local development, the `docker-compose.yml` file is configured to mount the local `public` and `nginx` directories into the container. This allows you to make changes to `nginx/default.conf` or the contents of `public` and see them reflected without rebuilding the image.

However, since the HTML, CSS, and JS files are in `src`, you have a few options to see your changes live:

1.  **Manual Copy**: The simplest method is to copy your changed files from `src` to `public` from the project root as you work.
    ```bash
    # Example: copy all src files to public
    cp -R lyrn-ai-site/src/* lyrn-ai-site/public/
    ```
2.  **File Watcher**: A better approach is to use a file watcher to automatically copy files from `src` to `public` when they change. You can use a tool like `watchman` or `nodemon`.
3.  **Rebuild Image**: You can always rebuild the image to include your latest changes from `src` using the `docker compose build` command.

**TLS / HTTPS:**

The Nginx configuration is set up for HTTPS, but you will need to provide your own TLS certificates. The `docker-compose.yml` expects them to be in a `lyrn-ai-site/docker/certs` directory. For local testing, you can generate self-signed certificates. For production, use a trusted authority like Let's Encrypt.
