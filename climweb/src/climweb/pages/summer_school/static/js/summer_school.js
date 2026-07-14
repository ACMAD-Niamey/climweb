/**
 * Sticky scrollspy nav for the Summer School page.
 *
 * The page is a single continuously-scrollable document (see
 * summer_school_page.html) - sections are never hidden/shown, the nav
 * only ever highlights whichever section is currently in view.
 *
 * This script is only <script>-included on summer_school_page.html, but
 * it guards defensively against missing sections/nav so it is harmless
 * if it ever ends up cached/loaded on another page.
 */
document.addEventListener('DOMContentLoaded', function () {
    var main = document.querySelector('main');
    var sections = main ? Array.prototype.slice.call(main.querySelectorAll('section[id]')) : [];

    // The hero's key-info card lives outside <main> but is still a valid
    // scrollspy target - the nav links to it like any other section.
    var keyInfoSection = document.getElementById('key-info');
    if (keyInfoSection) {
        sections.push(keyInfoSection);
    }

    var navLinks = Array.prototype.slice.call(document.querySelectorAll('.ss-nav-link[href^="#"]'));

    if (!sections.length || !navLinks.length) {
        return;
    }

    var navLinksById = {};
    navLinks.forEach(function (link) {
        var id = link.getAttribute('href').slice(1);
        navLinksById[id] = link;
    });

    function setActiveLink(id) {
        var targetLink = navLinksById[id];
        if (!targetLink) {
            return;
        }
        navLinks.forEach(function (link) {
            link.classList.remove('is-active');
        });
        targetLink.classList.add('is-active');
    }

    // rootMargin shrinks the effective viewport to a thin horizontal band
    // roughly centered on screen, so a section is marked "active" once it
    // occupies that central band rather than the instant it first appears.
    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                setActiveLink(entry.target.id);
            }
        });
    }, {
        root: null,
        rootMargin: '-40% 0px -55% 0px',
        threshold: 0
    });

    sections.forEach(function (section) {
        observer.observe(section);
    });
});
