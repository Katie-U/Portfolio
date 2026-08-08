// Theme switch. The theme itself is set by the inline script in <head> before
// first paint; this only handles clicks and keeps aria-checked truthful.
(function () {
    "use strict";

    var root = document.documentElement;
    var toggle = document.getElementById("themeToggle");

    if (!toggle) {
        return;
    }

    function sync() {
        toggle.setAttribute(
            "aria-checked",
            root.getAttribute("data-theme") === "dark" ? "true" : "false"
        );
    }

    sync();

    toggle.addEventListener("click", function () {
        var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
        root.setAttribute("data-theme", next);
        try {
            localStorage.setItem("theme", next);
        } catch (e) {
            // Private browsing can refuse storage; the theme still switches for
            // this page view, it just will not be remembered.
        }
        sync();
    });
})();

// Bolds the nav link whose section is currently on screen. The nav links point
// at "/#undergradDiv" style anchors, so this only finds targets on the home
// page and quietly does nothing everywhere else.
(function () {
    "use strict";

    var links = Array.prototype.slice.call(
        document.querySelectorAll("#navHeaders a.navLink")
    );

    var watched = links
        .map(function (link) {
            var hash = (link.getAttribute("href") || "").split("#")[1];
            var section = hash ? document.getElementById(hash) : null;
            return section ? { link: link, section: section } : null;
        })
        .filter(Boolean);

    if (!watched.length || !("IntersectionObserver" in window)) {
        return;
    }

    var observer = new IntersectionObserver(
        function (entries) {
            entries.forEach(function (entry) {
                watched.forEach(function (pair) {
                    if (pair.section === entry.target) {
                        pair.link.classList.toggle("active", entry.isIntersecting);
                    }
                });
            });
        },
        { rootMargin: "-45% 0px -45% 0px" }
    );

    watched.forEach(function (pair) {
        observer.observe(pair.section);
    });
})();
