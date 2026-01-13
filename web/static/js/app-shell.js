/**
 * SBS Deutschland – App Shell JavaScript
 * =======================================
 * Handles app navigation interactions.
 * Safe to load multiple times - checks for existing initialization.
 */

(function() {
  // Prevent double initialization
  if (window.sbsAppShellInitialized) return;
  window.sbsAppShellInitialized = true;

  function initAppShell() {
    // Elements
    var appSwitcherBtn = document.getElementById('appSwitcherBtn');
    var appSwitcherPanel = document.getElementById('appSwitcherPanel');
    var userBtn = document.getElementById('appUserBtn');
    var userMenu = document.getElementById('appUserMenu');
    var overlay = document.getElementById('appOverlay');

    // Helper: Close all menus
    function closeAllMenus() {
      if (appSwitcherPanel) appSwitcherPanel.classList.remove('open');
      if (userMenu) userMenu.classList.remove('open');
      if (overlay) overlay.classList.remove('active');
      document.querySelectorAll('.app-nav-dropdown').forEach(function(d) {
        d.classList.remove('open');
      });
    }

    // App Switcher Toggle
    if (appSwitcherBtn && appSwitcherPanel) {
      // Remove any existing inline onclick
      appSwitcherBtn.onclick = null;
      appSwitcherBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        var isOpen = appSwitcherPanel.classList.contains('open');
        closeAllMenus();
        if (!isOpen) {
          appSwitcherPanel.classList.add('open');
          if (overlay) overlay.classList.add('active');
        }
      });
    }

    // User Menu Toggle
    if (userBtn && userMenu) {
      // Remove any existing inline onclick
      userBtn.onclick = null;
      userBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        var isOpen = userMenu.classList.contains('open');
        closeAllMenus();
        if (!isOpen) {
          userMenu.classList.add('open');
          if (overlay) overlay.classList.add('active');
        }
      });
    }

    // Nav Dropdowns
    document.querySelectorAll('.app-nav-dropdown').forEach(function(dropdown) {
      var btn = dropdown.querySelector('.app-nav-dropdown-btn');
      if (btn) {
        // Remove any existing inline onclick
        btn.onclick = null;
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          var wasOpen = dropdown.classList.contains('open');
          // Close other dropdowns
          document.querySelectorAll('.app-nav-dropdown').forEach(function(d) {
            if (d !== dropdown) d.classList.remove('open');
          });
          // Toggle this dropdown
          dropdown.classList.toggle('open', !wasOpen);
        });
      }
    });

    // Close on overlay click
    if (overlay) {
      overlay.onclick = null;
      overlay.addEventListener('click', closeAllMenus);
    }

    // Close on outside click
    document.addEventListener('click', function(e) {
      // Close nav dropdowns
      if (!e.target.closest('.app-nav-dropdown')) {
        document.querySelectorAll('.app-nav-dropdown').forEach(function(d) {
          d.classList.remove('open');
        });
      }
      // Close user menu
      if (!e.target.closest('.app-user-btn') && !e.target.closest('.app-user-menu')) {
        if (userMenu) userMenu.classList.remove('open');
      }
      // Close app switcher
      if (!e.target.closest('.app-switcher-btn') && !e.target.closest('.app-switcher-panel')) {
        if (appSwitcherPanel) appSwitcherPanel.classList.remove('open');
      }
      // Update overlay
      if (overlay && appSwitcherPanel && userMenu) {
        if (!appSwitcherPanel.classList.contains('open') && !userMenu.classList.contains('open')) {
          overlay.classList.remove('active');
        }
      }
    });

    // Close on Escape
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        closeAllMenus();
      }
    });

    // Highlight current page in nav
    var currentPath = window.location.pathname;
    document.querySelectorAll('.app-nav-tab, .app-nav-dropdown-item').forEach(function(link) {
      var href = link.getAttribute('href');
      if (href === currentPath || (currentPath !== '/' && href && currentPath.startsWith(href))) {
        link.classList.add('active');
        // If in dropdown, also highlight parent
        var parentDropdown = link.closest('.app-nav-dropdown');
        if (parentDropdown) {
          var parentBtn = parentDropdown.querySelector('.app-nav-dropdown-btn');
          if (parentBtn) parentBtn.classList.add('active');
        }
      }
    });
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAppShell);
  } else {
    initAppShell();
  }
})();
