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

/**
 * Trainer card "view bio" popup — same open/close recipe used by
 * staff_page.html and dashboards/static/js/modal.js (Bulma's documented
 * modal pattern: toggle .is-active, driven by .js-modal-trigger /
 * data-target on the trigger and .modal-close / .modal-background on
 * the modal itself). Kept local to this file rather than promoted to a
 * shared static/js/modal.js, matching how the other two instances of
 * this pattern are each scoped to their own page's JS.
 */
document.addEventListener('DOMContentLoaded', function () {
    function openModal(el) {
        if (el) {
            el.classList.add('is-active');
        }
    }

    function closeModal(el) {
        if (el) {
            el.classList.remove('is-active');
        }
    }

    function closeAllModals() {
        document.querySelectorAll('.modal').forEach(closeModal);
    }

    document.querySelectorAll('.js-modal-trigger').forEach(function (trigger) {
        var target = document.getElementById(trigger.dataset.target);
        trigger.addEventListener('click', function () {
            // progressively.js never sees images inside a closed (display:none)
            // modal, so they'd stay stuck on their blurred placeholder forever -
            // force the swap ourselves for this modal's own .lazy_load images.
            if (target) {
                target.querySelectorAll('.lazy_load').forEach(function (img) {
                    img.setAttribute('src', img.getAttribute('data-progressive'));
                });
            }
            openModal(target);
        });
    });

    document.querySelectorAll('.modal-background, .modal-close').forEach(function (closeEl) {
        closeEl.addEventListener('click', function () {
            closeModal(closeEl.closest('.modal'));
        });
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeAllModals();
        }
    });
});

/**
 * Schedule day-tab switching — same pattern as events'
 * event_page.html (.tabs li -> toggles matching #id .content-tab),
 * scoped to .ss-schedule-tabs so it never touches the sticky nav's
 * own '.ss-nav-link' tabs above.
 */
document.addEventListener('DOMContentLoaded', function () {
    var dayTabs = document.querySelectorAll('.ss-schedule-tabs li');

    /**
     * A day's preview is capped at a fixed height (.ss-schedule-day-content,
     * see summer_school.css) so a heavy day doesn't push the whole page
     * down - "View full day schedule" (opening that day's modal) only
     * needs to appear when the content actually overflows the cap.
     * Only measurable while the panel is visible (display:block), so this
     * is called on load for the initially-active panel and again on every
     * tab switch for whichever panel just became active.
     */
    function updateScheduleTruncation(panel) {
        if (!panel) {
            return;
        }
        var content = panel.querySelector('.ss-schedule-day-content');
        var viewFullBtn = panel.querySelector('.ss-schedule-view-full');
        if (!content || !viewFullBtn) {
            return;
        }
        // Tolerance absorbs the ~10-15px of trailing margin that
        // overflow:hidden stops collapsing against its last child
        // (Bulma .columns gutters/margins) - that's noise, not real
        // overflow a visitor would notice as cut-off content.
        var isOverflowing = content.scrollHeight > content.clientHeight + 24;
        content.classList.toggle('is-truncated', isOverflowing);
        viewFullBtn.style.display = isOverflowing ? 'inline-block' : 'none';
    }

    document.querySelectorAll('.content-tab.is-active').forEach(updateScheduleTruncation);

    window.addEventListener('resize', function () {
        document.querySelectorAll('.content-tab.is-active').forEach(updateScheduleTruncation);
    });

    dayTabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            var dataId = tab.getAttribute('data-id');
            var targetPanel = dataId ? document.getElementById(dataId) : null;
            if (!targetPanel) {
                return;
            }

            dayTabs.forEach(function (t) {
                t.classList.remove('is-active');
            });
            tab.classList.add('is-active');

            document.querySelectorAll('.content-tab.is-active').forEach(function (panel) {
                panel.classList.remove('is-active');
            });
            targetPanel.classList.add('is-active');
            updateScheduleTruncation(targetPanel);
        });
    });
});
