(function () {
    "use strict";

    function addPhotoPreview(input) {
        var wrapper = document.createElement("div");
        var label = document.createElement("p");
        var frame = document.createElement("div");
        var image = document.createElement("img");
        var help = document.createElement("p");
        var objectUrl = null;

        wrapper.className = "photo-upload-preview";
        wrapper.hidden = true;
        label.className = "photo-preview-label";
        label.textContent = "Circular profile preview";
        frame.className = "photo-preview-frame";
        image.alt = "Preview of the selected profile photo";
        help.className = "photo-preview-help";
        help.textContent = "This preview matches the circular team photo. Make sure your full face is visible and centred.";

        frame.appendChild(image);
        wrapper.appendChild(label);
        wrapper.appendChild(frame);
        wrapper.appendChild(help);
        var fieldContainer = input.closest("p") || input.parentNode;
        fieldContainer.parentNode.insertBefore(wrapper, fieldContainer.nextSibling);

        input.addEventListener("change", function () {
            var file = input.files && input.files[0];
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
                objectUrl = null;
            }
            if (!file || !file.type.startsWith("image/")) {
                image.removeAttribute("src");
                wrapper.hidden = true;
                return;
            }
            objectUrl = URL.createObjectURL(file);
            image.src = objectUrl;
            wrapper.hidden = false;
        });

        window.addEventListener("pagehide", function () {
            if (objectUrl) URL.revokeObjectURL(objectUrl);
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll('input[type="file"][data-photo-preview="true"]').forEach(addPhotoPreview);
    });
}());
