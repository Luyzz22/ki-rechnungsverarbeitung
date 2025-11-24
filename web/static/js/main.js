(function() {
  'use strict';

  const savedTheme = localStorage.getItem('sbs-theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);

  document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const burger = document.getElementById('burger');
    const nav = document.getElementById('nav');

    if (themeToggle) {
      themeToggle.addEventListener('click', function() {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('sbs-theme', next);
      });
    }

    if (burger && nav) {
      burger.addEventListener('click', function() {
        nav.classList.toggle('active');
      });
    }

    // FAQ Accordion
    document.querySelectorAll('.faq-question').forEach(btn => {
      btn.addEventListener('click', function() {
        this.parentElement.classList.toggle('active');
      });
    });

    // Kontaktformular – optional /api/contact
    const form = document.getElementById('contact-form');
    if (form) {
      form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const btn = this.querySelector('.form-submit');
        const success = document.getElementById('form-success');
        const error = document.getElementById('form-error');

        btn.disabled = true;
        btn.textContent = 'Wird gesendet...';
        if (success) success.style.display = 'none';
        if (error) error.style.display = 'none';

        const data = Object.fromEntries(new FormData(this));

        try {
          const res = await fetch('/api/contact', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
          });

          if (res.ok) {
            if (success) success.style.display = 'block';
            this.reset();
          } else {
            throw new Error();
          }
        } catch (err) {
          if (error) error.style.display = 'block';
        } finally {
          btn.disabled = false;
          btn.textContent = 'Nachricht senden';
        }
      });
    }
  });
})();


/* NAV ACTIVE MARKER */
document.addEventListener('DOMContentLoaded', function () {
  try {
    var path = window.location.pathname;

    function normalize(p) {
      if (!p) return "/";
      p = p.split("?")[0].split("#")[0];
      p = p.replace(/\/+$/, "");
      return p === "" ? "/" : p;
    }

    var current = normalize(path);

    var links = document.querySelectorAll('.nav a[href]');
    links.forEach(function (link) {
      var href = link.getAttribute('href');
      if (!href) return;

      // externe Links (http/https) nicht markieren
      if (/^https?:\/\//i.test(href)) return;

      var target = normalize(href);

      // exakte Übereinstimmung oder Prefix-Match (z.B. /history vs /history/xyz)
      if (target === current || (target !== "/" && current.startsWith(target))) {
        link.classList.add('active');
      }
    });
  } catch (e) {
    console && console.warn && console.warn('nav active marker failed', e);
  }
});
