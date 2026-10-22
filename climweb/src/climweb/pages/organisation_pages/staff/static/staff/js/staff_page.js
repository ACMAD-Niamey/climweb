(() => {
    let activeModal = null;
    let activeTrigger = null;
    let wasClipped = false;
    const focusableSelector = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

    function closeModal() {
        if (!activeModal) return;
        activeModal.classList.remove('is-active');
        activeModal.setAttribute('aria-hidden', 'true');
        if (!wasClipped) document.documentElement.classList.remove('is-clipped');
        activeTrigger.focus();
        activeModal = null;
        activeTrigger = null;
    }

    function resetBiography(modal) {
        const bio = modal.querySelector('[data-staff-bio]');
        const toggle = modal.querySelector('[data-staff-bio-toggle]');
        if (!bio || !toggle) return;

        bio.classList.add('is-collapsed');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.textContent = toggle.dataset.readMore;
        toggle.hidden = bio.scrollHeight <= bio.clientHeight + 1;
    }

    document.querySelectorAll('[data-staff-bio-toggle]').forEach((toggle) => {
        const bio = document.getElementById(toggle.getAttribute('aria-controls'));
        if (!bio) return;
        toggle.addEventListener('click', () => {
            const willExpand = bio.classList.contains('is-collapsed');
            bio.classList.toggle('is-collapsed', !willExpand);
            toggle.setAttribute('aria-expanded', String(willExpand));
            toggle.textContent = willExpand ? toggle.dataset.readLess : toggle.dataset.readMore;
        });
    });

    document.querySelectorAll('[data-staff-modal]').forEach((trigger) => {
        const modal = document.getElementById(trigger.dataset.staffModal);
        if (!modal) return;
        trigger.addEventListener('click', () => {
            closeModal();
            activeModal = modal;
            activeTrigger = trigger;
            wasClipped = document.documentElement.classList.contains('is-clipped');
            modal.classList.add('is-active');
            modal.setAttribute('aria-hidden', 'false');
            document.documentElement.classList.add('is-clipped');
            resetBiography(modal);
            modal.querySelector('.modal-close').focus();
        });
        modal.querySelectorAll('[data-staff-close]').forEach((control) => {
            control.addEventListener('click', closeModal);
        });
    });

    document.addEventListener('keydown', (event) => {
        if (!activeModal) return;
        if (event.key === 'Escape') {
            event.preventDefault();
            closeModal();
        } else if (event.key === 'Tab') {
            const controls = Array.from(activeModal.querySelectorAll(focusableSelector))
                .filter((element) => element.getClientRects().length);
            const first = controls[0];
            const last = controls[controls.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
    });
})();
