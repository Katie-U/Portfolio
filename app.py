from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass
from urllib.parse import urljoin

from flask import Flask, Response, abort, redirect, render_template, request, url_for

# Windows has no registry entry for WebP, so the dev server hands these out as
# application/octet-stream. Register it up front rather than depending on
# whatever the host OS happens to know.
mimetypes.add_type("image/webp", ".webp")

app = Flask(__name__)

OWNER_NAME = "Katie Ulinski"
SITE_NAME = f"{OWNER_NAME} — Portfolio"
SITE_DESCRIPTION = (
    "Portfolio of Katie Ulinski, a Human-Computer Interaction masters student at "
    "Carnegie Mellon University, with a background in psychology, human factors "
    "and computer science education research."
)

OWNER_LINKEDIN = "https://www.linkedin.com/in/katie-ulinski"

# Shown on the contact page. Left blank the page falls back to LinkedIn alone,
# which is better than shipping a placeholder address that looks real.
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "")

# Absolute URLs are required in sitemaps, canonical tags and Open Graph tags.
# Set SITE_URL in the Railway dashboard to the site's real domain; without it we
# fall back to whichever host the request came in on, which is right for local
# development but lets duplicate hostnames each claim to be canonical.
CONFIGURED_SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")


@dataclass(frozen=True)
class Project:
    """A project shown as a card on the home page and on its own page.

    ``description`` is the long form that feeds the page's meta description and
    link previews. ``summary``, ``context`` and ``methods`` are what a reader
    sees on the card and in the specimen label at the top of the project page,
    so they stay short enough to scan.
    """

    slug: str
    title: str
    section: str
    template: str
    thumbnail: str
    description: str
    summary: str
    context: str
    methods: tuple[str, ...]


PROJECTS: tuple[Project, ...] = (
    Project(
        slug="hide",
        title="Humane Interface Design Enterprise",
        section="undergrad",
        template="projects/hide.html",
        thumbnail="hide-logo.webp",
        description=(
            "Human factors and usability work on the Humane Interface Design Enterprise "
            "at Michigan Tech: a class scheduling prototype for the computer science "
            "department and wireframes for a legal paper serving platform."
        ),
        summary=(
            "Human factors support for a student-run design and development studio, "
            "across a class scheduling prototype for the computer science department "
            "and wireframes for a legal paper serving platform."
        ),
        context="Michigan Tech · Enterprise program",
        methods=("Stakeholder interviews", "Prototyping", "Wireframing"),
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
        summary=(
            "A classroom tool that builds computational thinking outside computer "
            "science. Students diagram the relationships in a topic, give them "
            "measurements, then watch the system simulate what they described."
        ),
        context="Michigan Tech · CS education research lab",
        methods=("Subject-matter interviews", "Interface design", "Concept animation"),
    ),
    Project(
        slug="capstone",
        title="Stack Builder",
        section="grad",
        template="projects/capstone.html",
        thumbnail="south-fayette-logo.webp",
        description=(
            "Carnegie Mellon MHCI capstone with South Fayette High School: Stack Builder, "
            "a project aimed at increasing student autonomy and internal motivation so "
            "students can find their own path after high school."
        ),
        summary=(
            "Helps high school students see everything they have done — classes, "
            "extracurriculars and opportunities outside school — and find the patterns "
            "that point toward a path after graduation."
        ),
        context="Carnegie Mellon · MHCI capstone",
        methods=(
            "Participatory design",
            "Wizard of Oz",
            "Database design",
            "Recommendation system",
        ),
    ),
    Project(
        slug="cross-stitch",
        title="Cross Stitch Pattern Designer",
        section="grad",
        template="projects/cross-stitch.html",
        thumbnail="prototype-1-1.webp",
        description=(
            "A web app for designing block-based cross stitch patterns, with photo "
            "backgrounds and the official DMC colour palette, designed through three "
            "Figma prototypes and then built."
        ),
        summary=(
            "A block-pattern design tool with photo tracing and the official DMC thread "
            "palette, taken from three Figma prototypes through to a working build."
        ),
        context="Carnegie Mellon · Programming Usable Interfaces",
        methods=("Figma prototyping", "Front-end build"),
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
        summary=(
            "Physical games designed to change how a player thinks, on two-week "
            "iteration cycles — including a team game about holding difficult climate "
            "conversations across opposing perspectives."
        ),
        context="Carnegie Mellon · Transformational game design",
        methods=("Rapid iteration", "Playtesting", "Collaborative design"),
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
        "owner_linkedin": OWNER_LINKEDIN,
        "owner_email": OWNER_EMAIL,
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
    return render_template(
        "about.html",
        page_description=(
            f"About {OWNER_NAME}, a Human-Computer Interaction masters student at "
            "Carnegie Mellon University."
        ),
    )


@app.get("/contact")
def contact():
    return render_template(
        "contact.html",
        page_description=f"How to get in touch with {OWNER_NAME}.",
    )


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
    urls = [
        absolute_url(url_for("index")),
        absolute_url(url_for("about")),
        absolute_url(url_for("contact")),
    ] + [absolute_url(url_for("project", slug=project.slug)) for project in PROJECTS]
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
