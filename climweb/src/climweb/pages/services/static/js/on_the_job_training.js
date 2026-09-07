(function () {
  "use strict";

  function initGalleryModal() {
    var triggers = Array.from(document.querySelectorAll("[data-gallery-image]"));
    if (!triggers.length) return;

    var modal = document.getElementById("ojt-gallery-modal");
    if (!modal) return;

    var modalImg = document.getElementById("ojt-gallery-modal-img");
    var counter = document.getElementById("ojt-gallery-modal-counter");
    var prevBtn = modal.querySelector("[data-gallery-prev]");
    var nextBtn = modal.querySelector("[data-gallery-next]");
    var closeButtons = modal.querySelectorAll("[data-gallery-close]");

    var currentIndex = 0;

    function showImage(index) {
      if (index < 0) index = triggers.length - 1;
      if (index >= triggers.length) index = 0;
      currentIndex = index;

      var trigger = triggers[currentIndex];
      var fullSrc = trigger.getAttribute("data-full-src");
      var alt = trigger.getAttribute("data-alt") || "";

      modalImg.style.opacity = "0.5";
      modalImg.src = fullSrc;
      modalImg.alt = alt;
      modalImg.onload = function () {
        modalImg.style.opacity = "1";
      };

      if (counter) {
        counter.textContent = (currentIndex + 1) + " / " + triggers.length;
      }

      if (triggers.length <= 1) {
        if (prevBtn) prevBtn.style.display = "none";
        if (nextBtn) nextBtn.style.display = "none";
      } else {
        if (prevBtn) prevBtn.style.display = "flex";
        if (nextBtn) nextBtn.style.display = "flex";
      }
    }

    function openModal(index) {
      showImage(index);
      modal.classList.add("is-active");
      document.documentElement.classList.add("is-clipped");
      document.addEventListener("keydown", handleKeyDown);
    }

    function closeModal() {
      modal.classList.remove("is-active");
      document.documentElement.classList.remove("is-clipped");
      document.removeEventListener("keydown", handleKeyDown);
      if (modalImg) modalImg.src = "";
    }

    function handleKeyDown(e) {
      if (!modal.classList.contains("is-active")) return;
      if (e.key === "Escape" || e.keyCode === 27) {
        closeModal();
      } else if (e.key === "ArrowLeft" || e.keyCode === 37) {
        showImage(currentIndex - 1);
      } else if (e.key === "ArrowRight" || e.keyCode === 39) {
        showImage(currentIndex + 1);
      }
    }

    triggers.forEach(function (btn, i) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        openModal(i);
      });
    });

    closeButtons.forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        closeModal();
      });
    });

    if (prevBtn) {
      prevBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        showImage(currentIndex - 1);
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        showImage(currentIndex + 1);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initGalleryModal);
  } else {
    initGalleryModal();
  }
})();
