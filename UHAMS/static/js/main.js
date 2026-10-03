/*
 * static/js/main.js - the only JavaScript in the project.
 *
 * It powers the mobile navigation menu. On wide screens the sidebar is always visible and
 * this script does nothing. Below 900px the CSS hides the sidebar off-screen, and this script
 * opens/closes it by toggling the class "nav-open" on <body> (style.css reacts to that class).
 * The markup it works with (#nav-toggle button, #sidebar) lives in templates/base.html.
 */

// Mobile navigation: the sidebar slides in over the page below 900px.
(function () {
    // The hamburger button. It only exists in the signed-in layout.
    var toggle = document.getElementById('nav-toggle');
    // Signed-out pages have no sidebar or button, so there is nothing to set up.
    if (!toggle) return;

    // Single place that opens/closes the menu and keeps the button's accessibility
    // attributes truthful for screen readers (expanded state and label).
    function setOpen(open) {
        document.body.classList.toggle('nav-open', open);
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    }

    // Clicking the hamburger flips the current state.
    toggle.addEventListener('click', function () {
        setOpen(!document.body.classList.contains('nav-open'));
    });

    // Pressing Escape closes the menu.
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') setOpen(false);
    });

    // Tapping the dimmed page (anything outside the sidebar/toggle) closes the menu.
    document.addEventListener('click', function (e) {
        if (!document.body.classList.contains('nav-open')) return;
        if (!e.target.closest('#sidebar') && !e.target.closest('#nav-toggle')) setOpen(false);
    });
})();
