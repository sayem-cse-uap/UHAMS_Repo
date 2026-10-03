// Mobile navigation: the sidebar slides in over the page below 900px.
(function () {
    var toggle = document.getElementById('nav-toggle');
    if (!toggle) return;

    function setOpen(open) {
        document.body.classList.toggle('nav-open', open);
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    }

    toggle.addEventListener('click', function () {
        setOpen(!document.body.classList.contains('nav-open'));
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') setOpen(false);
    });

    // Tapping the dimmed page (anything outside the sidebar/toggle) closes the menu.
    document.addEventListener('click', function (e) {
        if (!document.body.classList.contains('nav-open')) return;
        if (!e.target.closest('#sidebar') && !e.target.closest('#nav-toggle')) setOpen(false);
    });
})();
