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
