(function () {
    const toggle = document.querySelector('.portal-menu-toggle');
    const sidebar = document.querySelector('.portal-sidebar');
    if (!toggle || !sidebar) return;
    toggle.addEventListener('click', function () {
        const open = sidebar.classList.toggle('is-open');
        toggle.setAttribute('aria-expanded', String(open));
    });

    function updateSectionNavigation() {
        if (!window.location.pathname.endsWith('/staff/')) return;
        const section = window.location.hash.replace('#', '') || 'dashboard';
        document.querySelectorAll('.portal-nav [data-section]').forEach(function (link) {
            link.classList.toggle('is-active', link.dataset.section === section);
        });
    }
    window.addEventListener('hashchange', updateSectionNavigation);
    updateSectionNavigation();
})();
