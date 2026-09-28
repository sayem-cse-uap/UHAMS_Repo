"use strict";

document.addEventListener("DOMContentLoaded", () => {
    // Highlight the nav link that matches the current page.
    const currentPath = window.location.pathname;
    document.querySelectorAll(".menu a[href]").forEach((link) => {
        const href = link.getAttribute("href");
        if (href && href !== "#" && href === currentPath) {
            link.classList.add("active");
            link.setAttribute("aria-current", "page");
        }
    });

    // Prevent accidental double-submits on forms.
    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", () => {
            const button = form.querySelector('button[type="submit"]');
            if (button) {
                // Defer so the form data is still submitted before disabling.
                setTimeout(() => {
                    button.disabled = true;
                    button.textContent = "Please wait…";
                }, 0);
            }
        });
    });
});
