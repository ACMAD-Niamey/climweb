(function () {
    "use strict";

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

