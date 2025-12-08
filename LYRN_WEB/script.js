/*
 * Global script for LYRN unified website
 *
 * This script implements a persistent theme engine and navigation
 * highlighting for all pages in the unified LYRN website. It reads
 * and writes the chosen theme (dark or light) from localStorage so
 * visitors see consistent styling across page loads. It also updates
 * the text on the top theme button to reflect the available mode
 * (e.g., "Light Mode" when currently in dark mode) and syncs the
 * state of the bottom slider. Finally it highlights the current
 * navigation link based on the page URL.
 */

document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;
  const themeButton = document.getElementById('themeButton');
  const themeToggle = document.getElementById('themeToggle');
  const ARCH_PAGES = ['embodied.html', 'memory.html', 'reflection.html', 'topic.html'];

  // Apply a given theme and update controls
  function applyTheme(theme) {
    body.setAttribute('data-theme', theme);
    localStorage.setItem('lyrn-theme', theme);
    // Update top button text to the opposite of current theme
    if (themeButton) {
      themeButton.textContent = theme === 'dark' ? 'LIGHT MODE' : 'DARK MODE';
    }
    // Update bottom slider checked state: slider ON means light mode
    if (themeToggle) {
      themeToggle.checked = (theme === 'light');
    }
  }

  // Initialize theme from localStorage or default to dark
  let savedTheme = localStorage.getItem('lyrn-theme');
  if (savedTheme !== 'light' && savedTheme !== 'dark') {
    savedTheme = 'dark';
  }
  applyTheme(savedTheme);

  // Top theme button click handler
  if (themeButton) {
    themeButton.addEventListener('click', () => {
      const currentTheme = body.getAttribute('data-theme') || 'dark';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      applyTheme(newTheme);
    });
  }

  // Bottom slider change handler
  if (themeToggle) {
    themeToggle.addEventListener('change', () => {
      const newTheme = themeToggle.checked ? 'light' : 'dark';
      applyTheme(newTheme);
    });
  }

  // Highlight the active nav link based on current page
  const currentFile = window.location.pathname.split('/').pop().toLowerCase();
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    const href = link.getAttribute('href');
    if (!href) return;
    // If this is the Architecture parent summary, handle separately
    if (link.id === 'nav-architecture') {
      if (ARCH_PAGES.includes(currentFile)) {
        link.classList.add('active');
      }
      return;
    }
    const linkFile = href.split('/').pop().toLowerCase();
    if (linkFile === currentFile) {
      link.classList.add('active');
    }
  });
});