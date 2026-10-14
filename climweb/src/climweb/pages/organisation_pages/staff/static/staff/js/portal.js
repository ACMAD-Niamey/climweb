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

    document.querySelectorAll('.portal-clickable-row[data-href]').forEach(function (row) {
        function openRow(event) {
            if (event.target.closest('a, button, input, select, textarea, label, form')) return;
            window.location.assign(row.dataset.href);
        }
        row.addEventListener('click', openRow);
        row.addEventListener('keydown', function (event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                openRow(event);
            }
        });
    });
})();
