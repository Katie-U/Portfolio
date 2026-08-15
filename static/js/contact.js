// Submits the contact form to the Flask handler with fetch, so a send never
// reloads the page. The form posts to the same URL on its own if this script
// does not run, and the server answers HTML in that case.
(function () {
    "use strict";

    var form = document.getElementById("contactForm");
    if (!form) {
        return;
    }

    var button = document.getElementById("submitButton");
    var status = document.getElementById("formStatus");
    var FIELDS = ["name", "email", "subject", "message"];

    function errorNodeFor(field) {
        return document.getElementById(field + "Error");
    }

    function clearErrors() {
        FIELDS.forEach(function (field) {
            var node = errorNodeFor(field);
            if (node) {
                node.textContent = "";
            }
            var input = form.elements[field];
            if (input) {
                input.removeAttribute("aria-invalid");
            }
        });
    }

    function showErrors(errors) {
        var first = null;
        FIELDS.forEach(function (field) {
            var message = errors[field];
            if (!message) {
                return;
            }
            var node = errorNodeFor(field);
            if (node) {
                node.textContent = message;
            }
            var input = form.elements[field];
            if (input) {
                input.setAttribute("aria-invalid", "true");
                first = first || input;
            }
        });
        if (first) {
            first.focus();
        }
    }

    function setStatus(message, ok) {
        status.textContent = message;
        status.classList.toggle("statusOk", ok);
        status.classList.toggle("statusError", !ok);
    }

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        clearErrors();
        setStatus("Sending...", true);
        button.disabled = true;

        var payload = {};
        FIELDS.concat(["website"]).forEach(function (field) {
            var input = form.elements[field];
            payload[field] = input ? input.value : "";
        });

        fetch(form.action, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
            .then(function (response) {
                // A proxy or a crash can answer with something that is not JSON,
                // so never assume the body parses.
                return response.json().catch(function () {
                    return { ok: false, message: "Something went wrong sending your message." };
                });
            })
            .then(function (data) {
                if (data.ok) {
                    form.reset();
                    setStatus(data.message || "Thanks! Your message is on its way.", true);
                    return;
                }
                if (data.errors) {
                    showErrors(data.errors);
                }
                setStatus(data.message || "Please fix the highlighted fields.", false);
            })
            .catch(function () {
                setStatus("Could not reach the server. Please try again.", false);
            })
            .then(function () {
                button.disabled = false;
            });
    });
})();
