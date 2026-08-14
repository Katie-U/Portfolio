from __future__ import annotations

import mimetypes
import os
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import resend
from dotenv import load_dotenv
from flask import Flask, Response, abort, redirect, render_template, request, url_for

# Local development reads secrets from .env; on Railway the same names are set
# as service variables, and load_dotenv leaves existing environment values
# alone, so this is a no-op there.
load_dotenv()

# Windows has no registry entry for WebP, so the dev server hands these out as
# application/octet-stream. Register it up front rather than depending on
# whatever the host OS happens to know.
mimetypes.add_type("image/webp", ".webp")

app = Flask(__name__)

OWNER_NAME = "Katie Ulinski"
SITE_NAME = f"{OWNER_NAME} — Portfolio"
SITE_DESCRIPTION = (
    "Portfolio of Katie Ulinski, a Human-Computer Interaction masters student at "
    "Carnegie Mellon University working in UX research and interaction design."
)

# Absolute URLs are required in sitemaps, canonical tags and Open Graph tags.
# Set SITE_URL in the Railway dashboard to the site's real domain; without it we
# fall back to whichever host the request came in on, which is right for local
# development but lets duplicate hostnames each claim to be canonical.
CONFIGURED_SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")

# Contact form delivery, via Resend. CONTACT_FROM_ADDRESS has to sit on a domain
# verified in the Resend dashboard -- the shared onboarding@resend.dev sender
# works without any DNS setup but will only deliver to the Resend account's own
# address, which is fine for testing and not for production.
CONTACT_FROM_ADDRESS = os.environ.get("CONTACT_FROM_ADDRESS", "onboarding@resend.dev")
CONTACT_TO_ADDRESS = os.environ.get("CONTACT_TO_ADDRESS", "")

# Long enough for a real message, short enough that nobody can post a novel.
FIELD_MAX_LENGTHS = {"name": 100, "email": 254, "subject": 150, "message": 5000}

# Deliberately loose: the only address format that really matters is the one
# Resend will accept as a reply-to, and over-strict regexes reject valid mail.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

CONTACT_SENT_MESSAGE = "Thanks! Your message is on its way."
CONTACT_UNAVAILABLE_MESSAGE = (
    "The contact form is not available right now. Please reach out on LinkedIn."
)
CONTACT_FAILED_MESSAGE = (
    "Something went wrong sending your message. Please try again in a moment."
)


@dataclass(frozen=True)
class Project:
    """A project shown as a card on the home page and on its own page."""

    slug: str
    title: str
    section: str
    template: str
    thumbnail: str
    description: str
    thumbnail_height: str | None = None
    card_id: str | None = None


PROJECTS: tuple[Project, ...] = (
    Project(
        slug="hide",
        title="Enterprise: HIDE",
        section="undergrad",
        template="projects/hide.html",
        thumbnail="hide-logo.webp",
        description=(
            "Human factors and usability work on the Humane Interface Design Enterprise "
            "at Michigan Tech: a class scheduling prototype for the computer science "
            "department and wireframes for a legal paper serving platform."
        ),
    ),
    Project(
        slug="modeler",
        title="Modeler",
        section="undergrad",
        template="projects/modeler.html",
        thumbnail="modeler-1.webp",
        description=(
            "User flow and interface design for Modeler, a tool that builds computational "
            "thinking skills in non-computer-science classrooms by letting students "
            "diagram, measure and simulate the relationships in a topic."
        ),
        thumbnail_height="225px",
        card_id="project2",
    ),
    Project(
        slug="capstone",
        title="Capstone: South Fayette",
        section="grad",
        template="projects/capstone.html",
        thumbnail="south-fayette-logo.webp",
        description=(
            "Carnegie Mellon MHCI capstone with South Fayette High School: Stack Builder, "
            "a project aimed at increasing student autonomy and internal motivation so "
            "students can find their own path after high school."
        ),
        thumbnail_height="224px",
    ),
    Project(
        slug="cross-stitch",
        title="Cross Stitch Pattern Website",
        section="grad",
        template="projects/cross-stitch.html",
        thumbnail="prototype-1-1.webp",
        description=(
            "A web app for designing block-based cross stitch patterns, with photo "
            "backgrounds and the official DMC colour palette, designed through three "
            "Figma prototypes and then built."
        ),
        thumbnail_height="210px",
    ),
    Project(
        slug="transformational-games",
        title="Transformational Games",
        section="grad",
        template="projects/transformational-games.html",
        thumbnail="carnegie-mellon.webp",
        description=(
            "Designing physical games that elicit change in the player, on two-week "
            "iteration cycles, including a team game about holding difficult "
            "conversations across differing perspectives on climate issues."
        ),
        thumbnail_height="225px",
    ),
)

PROJECTS_BY_SLUG = {project.slug: project for project in PROJECTS}

# The site used to be flat HTML files; keep those URLs working for anything
# already linking to them.
LEGACY_PAGES = {
    "project-description": "hide",
    "project-description-modeler": "modeler",
    "project-description-capstone": "capstone",
    "project-description-cross-stitch-website": "cross-stitch",
    "project-description-transformational-games": "transformational-games",
}


def projects_in(section: str) -> list[Project]:
    return [project for project in PROJECTS if project.section == section]


def site_url() -> str:
    """The site's base URL, with a trailing slash."""
    return CONFIGURED_SITE_URL + "/" if CONFIGURED_SITE_URL else request.url_root


def absolute_url(path: str) -> str:
    return urljoin(site_url(), path)


@app.context_processor
def seo_defaults():
    """Values every template's <head> needs.

    Templates override ``page_description`` and ``page_image`` by passing them to
    ``render_template``; the canonical URL is always the current path, so that
    query strings and the legacy hostnames never split a page's ranking.
    """
    return {
        "site_name": SITE_NAME,
        "owner_name": OWNER_NAME,
        "canonical_url": absolute_url(request.path),
        "page_description": SITE_DESCRIPTION,
        "page_image": absolute_url(url_for("static", filename="images-webp/hero.webp")),
    }


@app.get("/")
def index():
    return render_template(
        "index.html",
        undergrad_projects=projects_in("undergrad"),
        grad_projects=projects_in("grad"),
    )


@app.get("/about")
def about():
    return render_template("about.html")


@app.get("/contact")
def contact():
    return render_template("contact.html")

@app.get("/stackBuilder")
def stackBuilder():
    return render_template("projects/stackBuilder.html")

@app.get("/crossStitchWeb") 
def crossStitchWeb():
    return render_template("projects/crossStitchWeb.html")

@app.get("/ebikeDesign")
def ebikeDesign():
    return render_template("projects/ebikeDesign.html")

@app.get("/transformationalGames")
def transformationalGames():
    return render_template("projects/transformationalGames.html")

def validate_contact(form) -> tuple[dict[str, str], dict[str, str]]:
    """Split a submitted contact form into cleaned values and per-field errors.

    Errors are keyed by field name so the page can mark the offending input
    rather than showing one generic complaint at the top.
    """
    values: dict[str, str] = {}
    errors: dict[str, str] = {}

    for field, limit in FIELD_MAX_LENGTHS.items():
        value = (form.get(field) or "").strip()
        if not value:
            errors[field] = "This field is required."
        elif len(value) > limit:
            errors[field] = f"Please keep this under {limit} characters."
        values[field] = value

    if "email" not in errors and not EMAIL_PATTERN.match(values["email"]):
        errors["email"] = "Please enter a valid email address."

    return values, errors


def send_contact_email(values: dict[str, str]) -> None:
    """Hand a validated submission to Resend. Raises if it cannot be sent."""
    resend.api_key = os.environ["RESEND_API_KEY"]
    resend.Emails.send(
        {
            "from": f"{SITE_NAME} <{CONTACT_FROM_ADDRESS}>",
            "to": [CONTACT_TO_ADDRESS],
            # The visitor's own address, so replying from the inbox reaches them
            # directly. It is never used as the sender, which would fail SPF and
            # land the mail in spam.
            "reply_to": values["email"],
            "subject": f"Portfolio contact: {values['subject']}",
            "text": (
                f"From: {values['name']} <{values['email']}>\n"
                f"Subject: {values['subject']}\n\n"
                f"{values['message']}\n"
            ),
        }
    )


@app.post("/contact")
def contact_submit():
    """Email a contact form submission to CONTACT_TO_ADDRESS through Resend.

    Answers JSON to the page's fetch call and a re-rendered contact page to a
    plain form post, so the form still works with JavaScript switched off.
    """
    wants_json = request.is_json
    form = request.get_json(silent=True) or request.form

    def respond(status_code: int, message: str, errors: dict[str, str] | None = None):
        ok = status_code == 200
        if wants_json:
            payload = {"ok": ok, "message": message}
            if errors:
                payload["errors"] = errors
            return payload, status_code
        return (
            render_template(
                "contact.html",
                status_message=message,
                status_ok=ok,
                errors=errors or {},
                # Nobody should have to retype a message because one field was
                # wrong -- but a successful send starts from an empty form.
                values={} if ok else form,
            ),
            status_code,
        )

    # Bots fill in every field they can find. This one is hidden from people, so
    # anything in it means the submission is junk. Report success anyway: a bot
    # that gets an error learns to try again, one that gets a 200 does not.
    if (form.get("website") or "").strip():
        return respond(200, CONTACT_SENT_MESSAGE)

    values, errors = validate_contact(form)
    if errors:
        return respond(400, "Please fix the highlighted fields.", errors)

    if not os.environ.get("RESEND_API_KEY") or not CONTACT_TO_ADDRESS:
        app.logger.error(
            "Contact form is not configured: set RESEND_API_KEY and "
            "CONTACT_TO_ADDRESS in the environment."
        )
        return respond(503, CONTACT_UNAVAILABLE_MESSAGE)

    try:
        send_contact_email(values)
    except Exception:
        # Covers both Resend's own errors and the network failing underneath it;
        # either way the visitor gets the same message and the detail goes to
        # the Railway logs.
        app.logger.exception("Resend rejected a contact form submission")
        return respond(502, CONTACT_FAILED_MESSAGE)

    return respond(200, CONTACT_SENT_MESSAGE)


@app.get("/experiences")
def experiences():
    return render_template("experiences.html")


@app.get("/projects/<slug>")
def project(slug: str):
    selected = PROJECTS_BY_SLUG.get(slug)
    if selected is None:
        abort(404)
    return render_template(
        selected.template,
        project=selected,
        page_description=selected.description,
        page_image=absolute_url(
            url_for("static", filename=f"images-webp/{selected.thumbnail}")
        ),
    )


@app.get("/index.html")
def legacy_index():
    return redirect(url_for("index"), code=301)


@app.get("/<page>.html")
def legacy_project(page: str):
    slug = LEGACY_PAGES.get(page)
    if slug is None:
        abort(404)
    return redirect(url_for("project", slug=slug), code=301)


@app.get("/robots.txt")
def robots():
    body = render_template("robots.txt", sitemap_url=absolute_url("/sitemap.xml"))
    return Response(body, mimetype="text/plain")


@app.get("/sitemap.xml")
def sitemap():
    """Every indexable URL on the site.

    Generated from PROJECTS rather than hand-maintained, so adding a project
    cannot leave the sitemap stale. The legacy .html redirects are deliberately
    left out: a sitemap should only list canonical URLs.
    """
    urls = [absolute_url(url_for("index"))] + [
        absolute_url(url_for("project", slug=project.slug)) for project in PROJECTS
    ]
    body = render_template("sitemap.xml", urls=urls)
    return Response(body, mimetype="application/xml")


@app.get("/healthz")
def healthz():
    """Liveness endpoint for the Railway healthcheck."""
    return {"status": "ok"}


@app.errorhandler(404)
def page_not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=True)
