document.addEventListener("DOMContentLoaded", () => {
    const readMore = document.querySelector("[data-read-more]");
    if (readMore) {
        const content = readMore.querySelector("[data-read-more-content]");
        const toggle = readMore.querySelector("[data-read-more-toggle]");
        const label = toggle?.querySelector("[data-read-more-label]");

        if (content && toggle && content.scrollHeight > content.clientHeight + 2) {
            toggle.hidden = false;
            toggle.addEventListener("click", () => {
                const expanded = readMore.classList.toggle("is-expanded");
                readMore.classList.toggle("is-collapsed", !expanded);
                toggle.setAttribute("aria-expanded", String(expanded));
                if (label) {
                    label.textContent = expanded ? toggle.dataset.labelLess : toggle.dataset.labelMore;
                }
            });
        } else {
            readMore.classList.remove("is-collapsed");
        }
    }

    const carousel = document.querySelector("[data-schedule-carousel]");
    if (carousel) {
        const track = carousel.querySelector("[data-schedule-track]");
        const slides = [...carousel.querySelectorAll("[data-schedule-slide]")];
        const previous = document.querySelector("[data-schedule-previous]");
        const next = document.querySelector("[data-schedule-next]");
        const counter = document.querySelector("[data-schedule-counter]");
        let index = 0;
        let autoAdvance;
        const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        const update = () => {
            if (counter) counter.textContent = `${index + 1} / ${slides.length}`;
        };
        const goTo = (newIndex) => {
            index = (newIndex + slides.length) % slides.length;
            track?.scrollTo({ left: index * track.clientWidth, behavior: "smooth" });
            update();
        };
        const stopAutoAdvance = () => window.clearInterval(autoAdvance);
        const startAutoAdvance = () => {
            stopAutoAdvance();
            if (slides.length > 1 && !reducedMotion && !document.hidden) {
                autoAdvance = window.setInterval(() => goTo(index + 1), 6000);
            }
        };
        const moveManually = (step) => {
            goTo(index + step);
            startAutoAdvance();
        };

        previous?.addEventListener("click", () => moveManually(-1));
        next?.addEventListener("click", () => moveManually(1));
        carousel.addEventListener("mouseenter", stopAutoAdvance);
        carousel.addEventListener("mouseleave", startAutoAdvance);
        carousel.addEventListener("focusin", stopAutoAdvance);
        carousel.addEventListener("focusout", (event) => {
            if (!carousel.contains(event.relatedTarget)) startAutoAdvance();
        });
        document.addEventListener("visibilitychange", startAutoAdvance);
        window.addEventListener("resize", () => goTo(index));
        update();
        startAutoAdvance();
    }

    const eventList = document.querySelector("[data-side-events]");
    const viewButtons = [...document.querySelectorAll("[data-events-view]")];
    if (eventList && viewButtons.length) {
        viewButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const view = button.dataset.eventsView;
                eventList.classList.toggle("is-list", view === "list");
                eventList.classList.toggle("is-grid", view === "grid");
                viewButtons.forEach((item) => {
                    const active = item === button;
                    item.classList.toggle("is-active", active);
                    item.setAttribute("aria-pressed", String(active));
                });
            });
        });
    }
});
