/*
 * Global script for LYRN unified website
 * Includes Theme Engine, ScrollSpy Navigation, and Module Loader
 */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initScrollSpy();
  initBackToTop(); 
  initFloatingMenu();
  initFloatingToggle(); 
  initDashboardOverlay();
});

// --- Dashboard Overlay Logic ---
function initDashboardOverlay() {
    const overlay = document.getElementById('dashboard-overlay');
    const frame = document.getElementById('dashboard-frame');
    
    // Function to handle opening different dashboard versions
    function openDash(url) {
        if(frame.src.indexOf(url) === -1) { 
            frame.src = url;
        }
        overlay.classList.add('visible');
        document.body.classList.add('dashboard-open'); // LOCK SCROLL
    }

    // 1. Production Dashboard Triggers (Top Nav + Dock)
    const prodTriggers = ['nav-dashboard-btn', 'dock-dashboard-btn'];
    prodTriggers.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                openDash('dashboard.html');
            });
        }
    });

    // 2. Dev Dashboard Trigger (Footer EOF)
    const devBtn = document.getElementById('eof-trigger');
    if (devBtn) {
        devBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openDash('dev_db.html');
        });
    }

    // Listen for "CLOSE_DASHBOARD" message from iframe
    window.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'CLOSE_DASHBOARD') {
            overlay.classList.remove('visible');
            document.body.classList.remove('dashboard-open'); // UNLOCK SCROLL
        }
    });
}

// --- Floating Dock Logic (Drag, Snap to Grid, Persist) ---
function initFloatingToggle() {
    const dock = document.getElementById('floating-dock');
    const handle = document.getElementById('dock-handle');
    const content = document.getElementById('dock-content');
    
    if (!dock || !handle) return;

    let isDragging = false;
    let startX, startY, initialLeft, initialTop;
    let hasMoved = false;

    // Load saved position from LocalStorage
    const savedPos = localStorage.getItem('lyrn-dock-pos');
    if (savedPos) {
        try {
            const { left, top } = JSON.parse(savedPos);
            dock.style.bottom = 'auto';
            dock.style.right = 'auto';
            
            // Validate boundaries on load to prevent off-screen issues
            const maxLeft = window.innerWidth - 60; 
            const maxTop = window.innerHeight - 40;
            
            let safeLeft = Math.min(Math.max(20, left), maxLeft);
            let safeTop = Math.min(Math.max(20, top), maxTop);
            
            dock.style.left = `${safeLeft}px`;
            dock.style.top = `${safeTop}px`;
        } catch (e) {
            console.error("Failed to load dock position", e);
        }
    }

    // 1. Drag Functionality
    handle.addEventListener('mousedown', startDrag);
    handle.addEventListener('touchstart', startDrag, {passive: false});

    function startDrag(e) {
        // Prepare drag
        isDragging = true;
        hasMoved = false; 
        
        // Disable transition for snappy drag
        dock.classList.add('is-dragging');

        // Get mouse/touch position
        const clientX = e.type === 'touchstart' ? e.touches[0].clientX : e.clientX;
        const clientY = e.type === 'touchstart' ? e.touches[0].clientY : e.clientY;

        startX = clientX;
        startY = clientY;

        // Get current element position
        const rect = dock.getBoundingClientRect();
        initialLeft = rect.left;
        initialTop = rect.top;

        // Switch to absolute positioning
        dock.style.bottom = 'auto';
        dock.style.right = 'auto';
        dock.style.left = `${initialLeft}px`;
        dock.style.top = `${initialTop}px`;

        document.addEventListener('mousemove', onDrag);
        document.addEventListener('mouseup', stopDrag);
        document.addEventListener('touchmove', onDrag, {passive: false});
        document.addEventListener('touchend', stopDrag);
    }

    function onDrag(e) {
        if (!isDragging) return;
        e.preventDefault(); 

        const clientX = e.type === 'touchmove' ? e.touches[0].clientX : e.clientX;
        const clientY = e.type === 'touchmove' ? e.touches[0].clientY : e.clientY;

        const dx = clientX - startX;
        const dy = clientY - startY;

        // 2. Click vs Drag Threshold (5px)
        // Only consider it a drag if moved more than 5px total
        if (Math.abs(dx) + Math.abs(dy) > 5) {
            hasMoved = true;
        }

        // 3. Constrain to Viewport during drag
        let newLeft = initialLeft + dx;
        let newTop = initialTop + dy;

        const maxLeft = window.innerWidth - dock.offsetWidth;
        const maxTop = window.innerHeight - dock.offsetHeight;

        // Clamp
        if (newLeft < 0) newLeft = 0;
        if (newLeft > maxLeft) newLeft = maxLeft;
        if (newTop < 0) newTop = 0;
        if (newTop > maxTop) newTop = maxTop;

        dock.style.left = `${newLeft}px`;
        dock.style.top = `${newTop}px`;
        
        repositionNavOverlay();
    }

    function stopDrag() {
        isDragging = false;
        dock.classList.remove('is-dragging'); // Re-enable transition for snap

        document.removeEventListener('mousemove', onDrag);
        document.removeEventListener('mouseup', stopDrag);
        document.removeEventListener('touchmove', onDrag);
        document.removeEventListener('touchend', stopDrag);

        if (hasMoved) {
            // 4. Snap Behavior (GRID PATTERN)
            // Instead of snapping to sides, we snap to a grid so it stays inside
            const rect = dock.getBoundingClientRect();
            const gridSize = 40; // 40px grid squares
            const safeMargin = 20; // Keep at least 20px from edge

            // Get current raw position
            let currentLeft = rect.left;
            let currentTop = rect.top;

            // Round to nearest grid line
            let finalLeft = Math.round(currentLeft / gridSize) * gridSize;
            let finalTop = Math.round(currentTop / gridSize) * gridSize;

            // Enforce Safe Boundaries (User request: "stay inside of the page vertical")
            const maxLeft = window.innerWidth - rect.width - safeMargin;
            const maxTop = window.innerHeight - rect.height - safeMargin;

            // Clamp left
            if (finalLeft < safeMargin) finalLeft = safeMargin;
            if (finalLeft > maxLeft) finalLeft = maxLeft;

            // Clamp top
            if (finalTop < safeMargin) finalTop = safeMargin;
            if (finalTop > maxTop) finalTop = maxTop;

            // Apply Snap
            dock.style.left = `${finalLeft}px`;
            dock.style.top = `${finalTop}px`;
            
            // 5. Remember Position
            localStorage.setItem('lyrn-dock-pos', JSON.stringify({
                left: finalLeft,
                top: finalTop
            }));
            
            // Wait for transition, then update overlay
            setTimeout(repositionNavOverlay, 300);
        }
    }

    // Toggle Functionality (Only if NOT dragged)
    handle.addEventListener('click', (e) => {
        if (!hasMoved) {
            dock.classList.toggle('dock-collapsed');
            if (dock.classList.contains('dock-collapsed')) {
                 closeFloatingNav();
            }
        }
    });
}

// --- Floating Menu Logic ---
function initFloatingMenu() {
    const menuBtn = document.getElementById('floating-menu-btn');
    const navOverlay = document.getElementById('floating-nav-overlay');
    const dock = document.getElementById('floating-dock');
    
    if (!menuBtn || !navOverlay) return;

    menuBtn.addEventListener('click', (e) => {
        e.stopPropagation(); 
        const isVisible = navOverlay.classList.contains('visible');
        
        if (isVisible) {
            navOverlay.classList.remove('visible');
            menuBtn.innerText = '☰';
        } else {
            repositionNavOverlay();
            navOverlay.classList.add('visible');
            menuBtn.innerText = '✕';
        }
    });

    window.addEventListener('click', (e) => {
        if (!navOverlay.contains(e.target) && e.target !== menuBtn && !dock.contains(e.target)) {
            navOverlay.classList.remove('visible');
            menuBtn.innerText = '☰';
        }
    });
}

// Helper: Smartly position the overlay based on which side the dock is on
function repositionNavOverlay() {
    const dock = document.getElementById('floating-dock');
    const navOverlay = document.getElementById('floating-nav-overlay');
    
    if(dock && navOverlay) {
        const rect = dock.getBoundingClientRect();
        
        navOverlay.style.position = 'fixed';
        navOverlay.style.bottom = 'auto';
        navOverlay.style.right = 'auto';
        navOverlay.style.left = 'auto';

        // Check if dock is on the right side of the screen
        const isOnRight = rect.left > window.innerWidth / 2;

        // Position Logic:
        // Because dock content expands UP, we want the menu to align with the handle's vertical position
        
        if (isOnRight) {
            // Position Menu to the LEFT of the dock
            // 200px width + 15px gap
            navOverlay.style.left = `${rect.left - 215}px`;
        } else {
            // Position Menu to the RIGHT of the dock
            navOverlay.style.left = `${rect.right + 15}px`;
        }
        
        // Align bottom of menu with bottom of dock handle
        // We know the dock handle is at rect.bottom.
        // We want navOverlay.bottom = rect.bottom.
        // But we are setting 'top'.
        
        const overlayHeight = navOverlay.offsetHeight || 380; // approximate if hidden
        let topPos = rect.bottom - overlayHeight;

        // Constraint: Don't go off top of screen
        if (topPos < 20) topPos = 20;
        
        navOverlay.style.top = `${topPos}px`;
    }
}

window.closeFloatingNav = () => {
    const navOverlay = document.getElementById('floating-nav-overlay');
    const menuBtn = document.getElementById('floating-menu-btn');
    if (navOverlay) navOverlay.classList.remove('visible');
    if (menuBtn) menuBtn.innerText = '☰';
};

// --- Back To Top Logic ---
function initBackToTop() {
    const btn = document.getElementById('back-to-top');
    if (!btn) return;
    btn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// --- Theme Engine ---
function initTheme() {
  const body = document.body;
  const themeButton = document.getElementById('themeButton'); 
  
  const storedTheme = localStorage.getItem('lyrn-theme');
  let currentTheme = storedTheme || 'dark';
  applyTheme(currentTheme);

  // Sync to iframe on load
  const iframe = document.getElementById('module-frame-snapshot');
  if(iframe) {
      iframe.onload = () => {
          applyTheme(currentTheme);
      };
  }

  if (themeButton) {
    themeButton.addEventListener('click', () => {
      currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
      applyTheme(currentTheme);
    });
  }

  function applyTheme(theme) {
    body.setAttribute('data-theme', theme);
    if(themeButton) {
        themeButton.innerText = theme === 'dark' ? 'LIGHT MODE' : 'DARK MODE';
    }
    localStorage.setItem('lyrn-theme', theme);

    // Broadcast theme to modular iframes
    const frames = document.querySelectorAll('.module-iframe');
    frames.forEach(frame => {
        if(frame.contentWindow) {
            frame.contentWindow.postMessage({ type: 'THEME_CHANGE', theme: theme }, '*');
        }
    });
  }
}

// --- ScrollSpy Navigation ---
function initScrollSpy() {
  const navLinks = document.querySelectorAll('.nav-link');
  if (!navLinks.length) return;

  const sections = Array.from(navLinks)
    .map(link => {
      const href = link.getAttribute('href');
      if (!href || !href.startsWith('#')) return null;
      const id = href.substring(1);
      const section = document.getElementById(id);
      return section ? { link, section } : null;
    })
    .filter(Boolean);

  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      const href = link.getAttribute('href');
      if (href && href.startsWith('#')) {
        e.preventDefault();
        const targetId = href.substring(1);
        const target = document.getElementById(targetId);
        if (target) {
          const yOffset = -20; 
          const y = target.getBoundingClientRect().top + window.pageYOffset + yOffset;
          window.scrollTo({ top: y, behavior: 'smooth' });
        }
      }
    });
  });

  let lastActive = null;
  function onScroll() {
    const scrollPos = window.scrollY || window.pageYOffset;
    const offset = 120; 

    let current = null;
    for (const { link, section } of sections) {
      const top = section.offsetTop - offset;
      const bottom = top + section.offsetHeight;
      if (scrollPos >= top && scrollPos < bottom) {
        current = link;
        break;
      }
    }

    if (current !== lastActive) {
      if (lastActive) lastActive.classList.remove('active');
      if (current) current.classList.add('active');
      lastActive = current;
    }
  }

  window.addEventListener('scroll', onScroll);
  onScroll(); 
}

function showToast(msg, error=false) {
    // Only used for global notifications now, RWI has its own internal toaster
    console.log("Global Toast:", msg);
}