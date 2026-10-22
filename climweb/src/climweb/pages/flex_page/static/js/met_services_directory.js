document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-met-services-directory]").forEach((directory) => {
        const search = directory.querySelector("[data-met-services-search]");
        const cards = Array.from(directory.querySelectorAll("[data-met-service-card]"));
        const count = directory.querySelector("[data-met-services-count]");
        const empty = directory.querySelector("[data-met-services-empty]");

        if (!search) return;

        search.addEventListener("input", () => {
            const query = search.value.trim().toLocaleLowerCase();
            let visible = 0;

            cards.forEach((card) => {
                const matches = !query || card.dataset.searchText.includes(query);
                card.hidden = !matches;
                if (matches) visible += 1;
            });

            if (count) count.textContent = visible;
            if (empty) empty.hidden = visible !== 0;
        });
    });
});
