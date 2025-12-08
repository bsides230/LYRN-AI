# LYRN Website

This folder contains a unified, responsive website for the **Living Yield Relational Network (LYRN)**.  It consolidates the disparate prototype pages into a cohesive experience with a shared design system, single CSS file and global JavaScript for theme handling.  Key features include:

* **Common navigation** – All pages share a sidebar navigation with an accessible dropdown for the Architecture papers.  The current page is highlighted in purple.
* **Persistent theme engine** – A large button in the top‑right corner toggles between light and dark modes and a small slider appears in the footer.  Your choice of theme is remembered across pages via `localStorage`.
* **Responsive design** – Grids, typography and callouts adapt gracefully from desktop to mobile thanks to media queries and a single stylesheet (`style.css`).
* **Self‑contained assets** – Images (such as the logo) live in the `assets/` directory and are referenced relative to the HTML files.  There are no external CSS or JS dependencies aside from Google Fonts.

To preview the site locally, open `index.html` in your browser.  All internal links are relative so the site works via the file system or when served from GitHub Pages.

## Custom domain configuration

This repository includes a `CNAME` file specifying `lyrn-systems.com` as the custom domain.  To finish configuring the domain:

1. **Point DNS records** – In your DNS provider’s control panel, create a `CNAME` record for `lyrn-systems.com` that points to your GitHub Pages hostname (e.g. `username.github.io`).  If you want the root domain (without subdomain) to resolve correctly, some registrars require an `ALIAS` or `ANAME` record pointing to the same GitHub Pages hostname.
2. **Enable the domain in GitHub Pages** – On the repository page, go to **Settings** → **Pages**.  Select the `main` branch (or whichever branch hosts the site) as the source.  In the *Custom domain* field, enter `lyrn-systems.com` and save.  GitHub will automatically issue an SSL certificate once your DNS has propagated.
3. **Wait for propagation** – DNS changes can take a few minutes to a couple of hours.  Once complete, visiting `https://lyrn-systems.com` should serve this website.

For further details see the [GitHub Pages documentation](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site).