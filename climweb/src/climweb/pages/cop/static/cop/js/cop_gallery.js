(function () {
    "use strict";

    var carousel = document.querySelector("[data-gallery-carousel]");
    if (carousel) {
        var track = carousel.querySelector("[data-gallery-track]");
        var previousPage = carousel.querySelector("[data-gallery-scroll-previous]");
        var nextPage = carousel.querySelector("[data-gallery-scroll-next]");
        var scrolling;

        function updateCarouselButtons() {
            var maxScroll = Math.max(0, track.scrollWidth - track.clientWidth);
            previousPage.disabled = track.scrollLeft <= 2;
            nextPage.disabled = track.scrollLeft >= maxScroll - 2;
        }

        function scrollGallery(direction) {
            track.scrollBy({ left: direction * track.clientWidth, behavior: "smooth" });
        }

        previousPage.addEventListener("click", function () { scrollGallery(-1); });
        nextPage.addEventListener("click", function () { scrollGallery(1); });
        track.addEventListener("scroll", function () {
            window.clearTimeout(scrolling);
            scrolling = window.setTimeout(updateCarouselButtons, 80);
        });
        window.addEventListener("resize", updateCarouselButtons);
        updateCarouselButtons();
    }

    var dialog = document.querySelector("[data-gallery-dialog]");
    var triggers = Array.from(document.querySelectorAll("[data-gallery-image]"));
    if (!dialog || !triggers.length || typeof dialog.showModal !== "function") return;

    var image = dialog.querySelector("[data-gallery-dialog-image]");
    var counter = dialog.querySelector("[data-gallery-counter]");
    var current = 0;

    function show(index) {
        current = (index + triggers.length) % triggers.length;
        var trigger = triggers[current];
        image.src = trigger.dataset.src;
        image.alt = trigger.dataset.alt || "";
        counter.textContent = (current + 1) + " / " + triggers.length;
    }

    triggers.forEach(function (trigger, index) {
        trigger.addEventListener("click", function () {
            show(index);
            dialog.showModal();
        });
    });

    dialog.querySelector("[data-gallery-close]").addEventListener("click", function () { dialog.close(); });
    dialog.querySelector("[data-gallery-previous]").addEventListener("click", function () { show(current - 1); });
    dialog.querySelector("[data-gallery-next]").addEventListener("click", function () { show(current + 1); });
    dialog.addEventListener("click", function (event) { if (event.target === dialog) dialog.close(); });
    dialog.addEventListener("keydown", function (event) {
        if (event.key === "ArrowLeft") show(current - 1);
        if (event.key === "ArrowRight") show(current + 1);
    });
}());
