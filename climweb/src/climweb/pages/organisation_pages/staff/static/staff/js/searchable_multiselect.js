(function () {
    function enhanceSelect(select, index) {
        if (select.dataset.multiselectReady === 'true') return;
        select.dataset.multiselectReady = 'true';
        select.classList.add('search-multiselect-native');

        const wrapper = document.createElement('div');
        wrapper.className = 'search-multiselect';

        const control = document.createElement('div');
        control.className = 'search-multiselect-control';
        control.setAttribute('role', 'combobox');
        control.setAttribute('aria-haspopup', 'listbox');
        control.setAttribute('aria-expanded', 'false');

        const chips = document.createElement('div');
        chips.className = 'search-multiselect-chips';

        const input = document.createElement('input');
        input.type = 'search';
        input.className = 'search-multiselect-search';
        input.placeholder = select.dataset.searchPlaceholder || 'Search…';
        input.autocomplete = 'off';
        input.setAttribute('aria-label', input.placeholder);

        const menu = document.createElement('div');
        menu.className = 'search-multiselect-menu';
        menu.id = `search-multiselect-${index}`;
        menu.setAttribute('role', 'listbox');
        menu.setAttribute('aria-multiselectable', 'true');
        menu.hidden = true;
        control.setAttribute('aria-controls', menu.id);

        const empty = document.createElement('p');
        empty.className = 'search-multiselect-empty';
        empty.textContent = 'No matching staff members.';
        empty.hidden = true;

        control.append(chips, input);
        wrapper.append(control, menu);
        select.insertAdjacentElement('afterend', wrapper);

        const items = Array.from(select.options).map(function (option) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'search-multiselect-option';
            button.dataset.value = option.value;
            button.dataset.searchText = option.textContent.toLocaleLowerCase();
            button.setAttribute('role', 'option');
            const label = document.createElement('span');
            label.textContent = option.textContent;
            const check = document.createElement('span');
            check.className = 'search-multiselect-check';
            check.setAttribute('aria-hidden', 'true');
            check.textContent = '✓';
            button.append(label, check);
            button.addEventListener('click', function () {
                option.selected = !option.selected;
                select.dispatchEvent(new Event('change', { bubbles: true }));
                render();
                input.focus();
            });
            menu.append(button);
            return { option: option, button: button };
        });
        menu.append(empty);

        function openMenu() {
            menu.hidden = false;
            control.setAttribute('aria-expanded', 'true');
        }

        function closeMenu() {
            menu.hidden = true;
            control.setAttribute('aria-expanded', 'false');
        }

        function render() {
            chips.replaceChildren();
            items.forEach(function (item) {
                const selected = item.option.selected;
                item.button.classList.toggle('is-selected', selected);
                item.button.setAttribute('aria-selected', String(selected));
                if (!selected) return;

                const chip = document.createElement('span');
                chip.className = 'search-multiselect-chip';
                chip.append(document.createTextNode(item.option.textContent));
                const remove = document.createElement('button');
                remove.type = 'button';
                remove.setAttribute('aria-label', `Remove ${item.option.textContent}`);
                remove.textContent = '×';
                remove.addEventListener('click', function (event) {
                    event.stopPropagation();
                    item.option.selected = false;
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                    render();
                    input.focus();
                });
                chip.append(remove);
                chips.append(chip);
            });
        }

        function filterOptions() {
            const query = input.value.trim().toLocaleLowerCase();
            let visibleCount = 0;
            items.forEach(function (item) {
                const visible = item.button.dataset.searchText.includes(query);
                item.button.hidden = !visible;
                if (visible) visibleCount += 1;
            });
            empty.hidden = visibleCount !== 0;
            openMenu();
        }

        input.addEventListener('focus', openMenu);
        input.addEventListener('input', filterOptions);
        input.addEventListener('keydown', function (event) {
            const visible = items.filter(function (item) { return !item.button.hidden; });
            if (event.key === 'Escape') {
                closeMenu();
            } else if (event.key === 'ArrowDown' && visible.length) {
                event.preventDefault();
                visible[0].button.focus();
            } else if (event.key === 'Enter' && visible.length === 1) {
                event.preventDefault();
                visible[0].button.click();
            }
        });
        menu.addEventListener('keydown', function (event) {
            if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
            event.preventDefault();
            const visible = items.map(function (item) { return item.button; }).filter(function (button) { return !button.hidden; });
            const current = visible.indexOf(document.activeElement);
            const next = event.key === 'ArrowDown' ? Math.min(current + 1, visible.length - 1) : Math.max(current - 1, 0);
            if (visible[next]) visible[next].focus();
        });
        control.addEventListener('click', function (event) {
            if (!event.target.closest('.search-multiselect-chip button')) input.focus();
        });
        document.addEventListener('click', function (event) {
            if (!wrapper.contains(event.target)) closeMenu();
        });
        select.addEventListener('change', render);
        render();
    }

    document.querySelectorAll('select[data-searchable-multiselect="true"]').forEach(enhanceSelect);
})();
