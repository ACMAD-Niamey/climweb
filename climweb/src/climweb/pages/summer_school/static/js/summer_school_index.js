document.addEventListener('DOMContentLoaded', function () {
    var searchInput = document.getElementById('ss-search-input');
    var filterPills = document.getElementById('ss-filter-pills');
    var grid = document.getElementById('ss-cards-grid');
    var noResults = document.getElementById('ss-no-results');

    if (!grid) {
        return;
    }

    var cards = Array.prototype.slice.call(grid.querySelectorAll('.ss-index-card-col'));
    var activeFilter = 'all';

    function matchesFilter(card) {
        if (activeFilter === 'all') {
            return true;
        }
        if (activeFilter === 'upcoming') {
            return card.getAttribute('data-upcoming') === '1';
        }
        if (activeFilter === 'past') {
            return card.getAttribute('data-upcoming') === '0';
        }
        var tags = (card.getAttribute('data-tags') || '').split(/\s+/);
        return tags.indexOf(activeFilter) !== -1;
    }

    function matchesSearch(card, query) {
        if (!query) {
            return true;
        }
        var haystack = card.getAttribute('data-search') || '';
        return haystack.indexOf(query) !== -1;
    }

    function applyFilters() {
        var query = searchInput ? searchInput.value.trim().toLowerCase() : '';
        var visibleCount = 0;

        cards.forEach(function (card) {
            var visible = matchesFilter(card) && matchesSearch(card, query);
            card.hidden = !visible;
            if (visible) {
                visibleCount += 1;
            }
        });

        if (noResults) {
            noResults.hidden = visibleCount !== 0;
        }
    }

    if (searchInput) {
        searchInput.addEventListener('input', applyFilters);
    }

    if (filterPills) {
        filterPills.addEventListener('click', function (event) {
            var pill = event.target.closest('.ss-filter-pill');
            if (!pill) {
                return;
            }
            filterPills.querySelectorAll('.ss-filter-pill').forEach(function (btn) {
                btn.classList.remove('is-active');
            });
            pill.classList.add('is-active');
            activeFilter = pill.getAttribute('data-filter');
            applyFilters();
        });
    }
});
