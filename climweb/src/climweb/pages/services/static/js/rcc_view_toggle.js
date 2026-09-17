document.addEventListener('DOMContentLoaded', () => {
    const viewToggleBtns = document.querySelectorAll('.rcc-view-toggle__btn');
    if (!viewToggleBtns.length) return;

    const dataContainer = document.querySelector('.rcc-country-grid, .rcc-station-grid');
    if (!dataContainer) return;

    const storageKey = 'rcc-data-view-preference';
    const savedView = localStorage.getItem(storageKey) || 'grid';

    function setView(viewType) {
        if (viewType === 'list') {
            dataContainer.classList.add('is-list-view');
        } else {
            dataContainer.classList.remove('is-list-view');
        }

        viewToggleBtns.forEach(btn => {
            if (btn.dataset.view === viewType) {
                btn.classList.add('is-active');
            } else {
                btn.classList.remove('is-active');
            }
        });

        localStorage.setItem(storageKey, viewType);
    }

    // Set initial view
    setView(savedView);

    // Bind click events
    viewToggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            setView(btn.dataset.view);
        });
    });
});
