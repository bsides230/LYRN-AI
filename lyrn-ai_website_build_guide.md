
# LYRN‑AI Website Build Guide (Self‑Hosted)

**Domain:** `lyrn-ai.com`  
**Registrar/DNS:** GoDaddy (DNS managed at GoDaddy, site hosted on your own server)  
**Primary Brand Color:** **LYRN Purple `#880ed4`**  
**Assets provided:**  
- `lyrn_logo_light.png` (white background) – *source:* `assets/lyrn_logo.png` (rename on copy)  
- `lyrn_logo_dark.jpg` (black background) – *source:* `assets/lyrn_logo copy.jpg` (rename on copy)  
- `splash.mp4` – *source:* `assets/LYRN_Launcher_Splash_Screen_Animation.mp4`

> This guide is written for Jules to implement quickly. It uses a **static site** (HTML/CSS/JS) behind **Nginx** in Docker. Swap pieces as needed.

---

## 0) Goals
- Launch a fast, accessible landing site for LYRN‑AI with a cinematic splash.
- Self‑host on a Linux box with Nginx + TLS.
- Keep a **clean repo** and **repeatable deployment** (Docker Compose).
- Make all branding configurable via CSS variables.

---

## 1) Project Structure

```
lyrn-ai-site/
├─ public/
│  ├─ img/
│  │  ├─ lyrn_logo_light.png
│  │  └─ lyrn_logo_dark.jpg
│  ├─ video/
│  │  └─ splash.mp4
│  ├─ favicon/              # generated from the logo
│  ├─ robots.txt
│  ├─ sitemap.xml
│  └─ .well-known/          # for ACME HTTP‑01 if needed
├─ src/
│  ├─ css/
│  │  └─ styles.css
│  ├─ js/
│  │  └─ main.js
│  ├─ index.html
│  ├─ about.html
│  ├─ tech.html             # whitepaper / architecture overview
│  └─ contact.html
├─ nginx/
│  └─ default.conf
├─ docker/
│  ├─ Dockerfile
│  └─ docker-compose.yml
└─ README.md
```

**Copy assets into the repo:**
- From this workspace:  
  - `/mnt/data/lyrn_logo.png → public/img/lyrn_logo_light.png`  
  - `/mnt/data/lyrn_logo copy.jpg → public/img/lyrn_logo_dark.jpg`  
  - `/mnt/data/LYRN_Launcher_Splash_Screen_Animation.mp4 → public/video/splash.mp4`

---

## 2) Design System

### Colors (CSS Variables)
```css
:root{
  --lyrn-purple: #880ed4;
  --purple-900: #5a078f;
  --purple-700: #6e0ab1;
  --purple-300: #b97ff0;

  --bg: #0a0a0a;         /* default dark background */
  --surface: #111214;
  --text: #f6f7fb;
  --muted: #b8b8c2;
  --accent: var(--lyrn-purple);

  /* focus and states */
  --focus: #ffffff;
  --ok: #00c27a;
  --warn: #ffb020;
  --error: #ff4d4d;
}
```

### Typography
- Primary: **Inter** (UI)  
- Alternate: **Space Grotesk** (headlines)  
- Fallback: `system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif`

Include via HTML `<link>` using Google Fonts or self‑host the font files.

### Buttons
```css
.button {
  display:inline-flex; align-items:center; gap:.5rem;
  padding:.85rem 1.25rem; border-radius:999px;
  background:var(--accent); color:#fff; font-weight:600;
  border:1px solid transparent; text-decoration:none;
}
.button:hover { filter:brightness(1.05); }
.button:focus-visible { outline:2px solid var(--focus); outline-offset:3px; }
```

### Accessibility
- Maintain **contrast ≥ 4.5:1** for normal text, **≥ 3:1** for large.  
- Provide keyboard focus styles, `lang="en"`, and `alt` for images.  
- Video must be **muted** to allow autoplay, with a **Pause** control and **Skip** link.

---

## 3) HTML – Home (splash) `src/index.html`

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LYRN‑AI</title>
  <link rel="preload" as="video" href="/video/splash.mp4" type="video/mp4">
  <link rel="stylesheet" href="/css/styles.css" />
  <link rel="icon" href="/favicon/favicon.ico">
</head>
<body>
  <a class="skip" href="#main">Skip</a>

  <video id="bgVideo" class="bg-video" playsinline autoplay muted loop>
    <source src="/video/splash.mp4" type="video/mp4" />
  </video>

  <header class="site-header">
    <img class="logo" src="/img/lyrn_logo_dark.jpg" width="56" height="56" alt="LYRN‑AI logo" />
    <nav class="nav">
      <a href="/">Home</a>
      <a href="/about.html">About</a>
      <a href="/tech.html">Tech</a>
      <a href="/contact.html">Contact</a>
    </nav>
  </header>

  <main id="main" class="hero">
    <h1>Living&nbsp;Yield&nbsp;Relational&nbsp;Network</h1>
    <p>Local‑first cognition. Persistent memory. Hot‑swappable models.</p>
    <div class="cta-row">
      <a class="button" href="/tech.html">Explore the tech</a>
      <button class="button ghost" id="pauseVideo">Pause</button>
    </div>
  </main>

  <script src="/js/main.js"></script>
</body>
</html>
```

### CSS – core `src/css/styles.css`
```css
@font-face{font-family:Inter;src:local("Inter");font-display:swap;}
:root{ /* see variables above; paste or import */ }

*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0; background:var(--bg); color:var(--text);
  font: 16px/1.6 Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}

.skip{position:absolute; left:-9999px; top:auto}
.skip:focus{left:1rem; top:1rem; background:#000; color:#fff; padding:.5rem}

.bg-video{
  position:fixed; right:0; bottom:0; min-width:100%; min-height:100%;
  object-fit:cover; filter:brightness(.5) saturate(1.1);
}

.site-header{
  position:fixed; top:0; left:0; right:0;
  display:flex; align-items:center; justify-content:space-between;
  padding:1rem 1.25rem; background:linear-gradient(180deg, rgba(0,0,0,.55), rgba(0,0,0,0));
}

.logo{display:block}

.nav a{
  color:var(--text); text-decoration:none; margin:0 .75rem; font-weight:600;
}
.nav a:hover{color:var(--accent)}

.hero{
  position:relative; z-index:1; min-height:100vh;
  display:grid; place-items:center; text-align:center; padding:8rem 1.5rem 4rem;
}

h1{font-size:clamp(2.6rem, 6vw, 5rem); margin:.25rem 0}
p{max-width:58ch; margin:.5rem auto 1.25rem; color:var(--muted)}

.cta-row{display:flex; gap:1rem; justify-content:center; flex-wrap:wrap}
.button{ /* from design system */ }
.button.ghost{background:transparent; border-color:var(--accent); color:var(--accent)}
```

### JS – `src/js/main.js`
```js
const v = document.getElementById('bgVideo');
const btn = document.getElementById('pauseVideo');
if (v && btn){
  btn.addEventListener('click', () => {
    if (v.paused){ v.play(); btn.textContent = 'Pause'; }
    else { v.pause(); btn.textContent = 'Play'; }
  });
}
```

---

## 4) Additional Pages

Create `about.html`, `tech.html`, `contact.html` with the same header/footer. Keep content semantic (`<section>`, `<article>`, `<footer>`).

**Placeholders to wire:**
- `tech.html` → links to whitepaper(s) and demo videos.
- `contact.html` → email or form endpoint (Netlify Forms or self‑hosted later).

---

## 5) Favicon

Generate favicons from `public/img/lyrn_logo_light.png` (square). Favor 512×512 PNG. Put outputs in `public/favicon/` and reference `/favicon/favicon.ico` in the `<head>` of each page.

---

## 6) GoDaddy DNS (Point to Self‑Hosted Server)

1. Log in → Domains → **lyrn-ai.com** → **DNS**.  
2. Records to create/update:
   - **A**: `@` → `YOUR_SERVER_IPV4` (e.g., `12.34.56.78`), **TTL 600s**.
   - **AAAA** *(optional)*: `@` → `YOUR_SERVER_IPV6`.
   - **CNAME**: `www` → `lyrn-ai.com`.
3. Save. Propagation can take a few minutes to a few hours.
4. If you later move DNS off GoDaddy, update **nameservers** instead and replicate these records there.

---

## 7) Nginx + TLS (Dockerized)

### `docker/Dockerfile`
```dockerfile
FROM nginx:1.27-alpine
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY public /usr/share/nginx/html
```

### `docker/docker-compose.yml`
```yaml
version: "3.9"
services:
  web:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: lyrn-ai-web
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ../public:/usr/share/nginx/html:ro
      - ./nginx:/etc/nginx/conf.d:ro
      - ./certs:/etc/letsencrypt:ro
    restart: unless-stopped
```

### `nginx/default.conf`
```nginx
server {
  listen 80;
  listen [::]:80;
  server_name lyrn-ai.com www.lyrn-ai.com;
  location /.well-known/acme-challenge/ { root /usr/share/nginx/html; }
  location / { return 301 https://$host$request_uri; }
}

server {
  listen 443 ssl http2;
  listen [::]:443 ssl http2;
  server_name lyrn-ai.com www.lyrn-ai.com;

  ssl_certificate     /etc/letsencrypt/live/lyrn-ai.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/lyrn-ai.com/privkey.pem;

  add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

  root /usr/share/nginx/html;
  index index.html;

  gzip on;
  gzip_types text/css application/javascript application/json image/svg+xml;
  location / { try_files $uri $uri/ =404; }
}
```

### TLS via Certbot (HTTP‑01)
On the host:
```bash
sudo docker compose -f docker/docker-compose.yml up -d
sudo apt-get update && sudo apt-get install -y certbot
sudo certbot certonly --webroot -w /path/to/repo/public -d lyrn-ai.com -d www.lyrn-ai.com
# after certs are issued, restart stack
sudo docker compose -f docker/docker-compose.yml restart
```

> Renewals: add a cron job to run `certbot renew` daily; it only renews when due.

---

## 8) Build & Deploy

```bash
# 1) copy assets
cp /mnt/data/lyrn_logo.png public/img/lyrn_logo_light.png
cp "/mnt/data/lyrn_logo copy.jpg" public/img/lyrn_logo_dark.jpg
cp /mnt/data/LYRN_Launcher_Splash_Screen_Animation.mp4 public/video/splash.mp4

# 2) local preview (simple)
python3 -m http.server -d public 8080

# 3) dockerized deploy
cd docker && docker compose up -d --build
```

**Performance tips**
- Keep `splash.mp4` ≤ ~6–10 MB (H.264, 1080p, ~3–6 Mbps). Provide a static image fallback if needed.
- Serve images as optimized PNG/JPEG/WebP. Use `<img width height>` to avoid CLS.
- Add basic SEO: `<meta name="description">`, `sitemap.xml`, `robots.txt`.

---

## 9) Content Checklist

- [ ] Replace placeholder copy on Home/Tech/About/Contact.
- [ ] Link to demos and whitepaper(s).
- [ ] Generate favicons.
- [ ] Confirm DNS propagation.
- [ ] Issue TLS certs and force HTTPS.
- [ ] Lighthouse pass: **Performance ≥ 90**, **Accessibility ≥ 95**.
- [ ] 404 page and basic logging.

---

## 10) Future Enhancements

- Blogging docs via static generator (Astro/11ty) while keeping the same Nginx stack.
- i18n later.
- Netdata/Prometheus for uptime & metrics.
- Form handler (serverless or minimal Flask/Express micro‑service behind Nginx).

---

## Appendix A — Minimal `about.html` (pattern)

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>About — LYRN‑AI</title>
  <link rel="stylesheet" href="/css/styles.css" />
</head>
<body>
  <header class="site-header">...</header>
  <main class="page">
    <h1>About LYRN‑AI</h1>
    <p>LYRN is a local‑first cognition framework with persistent memory...</p>
  </main>
</body>
</html>
```

---

### Notes for Jules
- Keep PRs small and atomic.  
- Add `README.md` with dev commands and deployment notes.  
- Use `prettier` for HTML/CSS/JS formatting.
