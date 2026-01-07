/**
 * SBS Deutschland – App Shell JavaScript
 * =======================================
 * Interaktionen für App-Navigation.
 */

document.addEventListener('DOMContentLoaded', function() {
  // Elements
  const appSwitcherBtn = document.getElementById('appSwitcherBtn');
  const appSwitcherPanel = document.getElementById('appSwitcherPanel');
  const userBtn = document.getElementById('appUserBtn');
  const userMenu = document.getElementById('appUserMenu');
  const overlay = document.getElementById('appOverlay');
  const navDropdowns = document.querySelectorAll('.app-nav-dropdown');

  // App Switcher Toggle
  if (appSwitcherBtn && appSwitcherPanel) {
    appSwitcherBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      const isOpen = appSwitcherPanel.classList.contains('open');
      closeAllMenus();
      if (!isOpen) {
        appSwitcherPanel.classList.add('open');
        overlay.classList.add('active');
      }
    });
  }

  // User Menu Toggle
  if (userBtn && userMenu) {
    userBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      const isOpen = userMenu.classList.contains('open');
      closeAllMenus();
      if (!isOpen) {
        userMenu.classList.add('open');
        overlay.classList.add('active');
      }
    });
  }

  // Nav Dropdowns
  navDropdowns.forEach(function(dropdown) {
    const btn = dropdown.querySelector('.app-nav-dropdown-btn');
    if (btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        const isOpen = dropdown.classList.contains('open');
        closeNavDropdowns();
        if (!isOpen) {
          dropdown.classList.add('open');
        }
      });
    }
  });

  // Close on overlay click
  if (overlay) {
    overlay.addEventListener('click', closeAllMenus);
  }

  // Close on outside click
  document.addEventListener('click', function(e) {
    if (!e.target.closest('.app-nav-dropdown')) {
      closeNavDropdowns();
    }
  });

  // Close on Escape
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      closeAllMenus();
    }
  });

  // Helper Functions
  function closeAllMenus() {
    if (appSwitcherPanel) appSwitcherPanel.classList.remove('open');
    if (userMenu) userMenu.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
    closeNavDropdowns();
  }

  function closeNavDropdowns() {
    navDropdowns.forEach(function(d) {
      d.classList.remove('open');
    });
  }

  // Highlight current page in nav
  const currentPath = window.location.pathname;
  document.querySelectorAll('.app-nav-tab, .app-nav-dropdown-item').forEach(function(link) {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
      // If in dropdown, also highlight parent
      const parentDropdown = link.closest('.app-nav-dropdown');
      if (parentDropdown) {
        parentDropdown.querySelector('.app-nav-dropdown-btn').classList.add('active');
      }
    }
  });
});

// Utility: Get user initials
function getUserInitials(name) {
  if (!name) return '?';
  const parts = name.trim().split(' ');
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
}
