from __future__ import annotations

import os
from dataclasses import dataclass

from flask import Flask, abort, redirect, render_template, url_for

app = Flask(__name__)


@dataclass(frozen=True)
class Project:
    """A project shown as a card on the home page and on its own page."""

    slug: str
    title: str
    section: str
    template: str
    thumbnail: str
    thumbnail_height: str | None = None
    card_id: str | None = None


PROJECTS: tuple[Project, ...] = (
    Project(
        slug="hide",
        title="Enterprise: HIDE",
        section="undergrad",
        template="projects/hide.html",
        thumbnail="hide-logo.png",
    ),
    Project(
        slug="modeler",
        title="Modeler",
        section="undergrad",
        template="projects/modeler.html",
        thumbnail="modeler-1.jpg",
        thumbnail_height="225px",
        card_id="project2",
    ),
    Project(
        slug="capstone",
        title="Capstone: South Fayette",
        section="grad",
        template="projects/capstone.html",
        thumbnail="south-fayette-logo.png",
        thumbnail_height="224px",
    ),
    Project(
        slug="cross-stitch",
        title="Cross Stitch Pattern Website",
        section="grad",
        template="projects/cross-stitch.html",
        thumbnail="prototype-1-1.jpg",
        thumbnail_height="210px",
    ),
    Project(
        slug="transformational-games",
        title="Transformational Games",
        section="grad",
        template="projects/transformational-games.html",
        thumbnail="carnegie-mellon.png",
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


@app.get("/")
def index():
    return render_template(
        "index.html",
        undergrad_projects=projects_in("undergrad"),
        grad_projects=projects_in("grad"),
    )


@app.get("/projects/<slug>")
def project(slug: str):
    selected = PROJECTS_BY_SLUG.get(slug)
    if selected is None:
        abort(404)
    return render_template(selected.template, project=selected)


@app.get("/index.html")
def legacy_index():
    return redirect(url_for("index"), code=301)


@app.get("/<page>.html")
def legacy_project(page: str):
    slug = LEGACY_PAGES.get(page)
    if slug is None:
        abort(404)
    return redirect(url_for("project", slug=slug), code=301)


@app.get("/healthz")
def healthz():
    """Liveness endpoint for the Railway healthcheck."""
    return {"status": "ok"}


@app.errorhandler(404)
def page_not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=True)
