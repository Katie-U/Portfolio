"""Smoke tests: every page renders and every asset it points at exists."""

import re
from pathlib import Path

import pytest

from app import PROJECTS, app

STATIC_ROOT = Path(app.root_path) / "static"
ASSET_PATTERN = re.compile(r'(?:src|href|poster)\s*=\s*"(/static/[^"]+)"')


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def page_paths():
    return ["/", "/about", "/contact"] + [
        f"/projects/{project.slug}" for project in PROJECTS
    ]


@pytest.mark.parametrize("path", page_paths())
def test_page_renders(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", page_paths())
def test_referenced_assets_exist(client, path):
    html = client.get(path).get_data(as_text=True)
    referenced = ASSET_PATTERN.findall(html)
    assert referenced, f"{path} references no static assets"
    for url in referenced:
        asset = STATIC_ROOT / url.removeprefix("/static/")
        assert asset.is_file(), f"{path} references missing asset {url}"


def test_every_project_is_linked_from_home(client):
    html = client.get("/").get_data(as_text=True)
    for project in PROJECTS:
        # Tolerate whitespace around the "=" so the assertion tracks the link
        # rather than the template's formatting.
        assert re.search(rf'href\s*=\s*"/projects/{project.slug}"', html)


def test_legacy_urls_redirect(client):
    response = client.get("/project-description-modeler.html")
    assert response.status_code == 301
    assert response.headers["Location"] == "/projects/modeler"

    assert client.get("/index.html").headers["Location"] == "/"


def test_unknown_page_returns_404(client):
    assert client.get("/projects/nope").status_code == 404
    assert client.get("/whatever.html").status_code == 404


def test_healthcheck(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}


def test_robots_txt(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response.mimetype == "text/plain"

    body = response.get_data(as_text=True)
    assert "User-agent: *" in body
    assert "Sitemap: http://localhost/sitemap.xml" in body


def test_sitemap_lists_every_page(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert response.mimetype == "application/xml"

    body = response.get_data(as_text=True)
    assert "<loc>http://localhost/</loc>" in body
    for project in PROJECTS:
        assert f"<loc>http://localhost/projects/{project.slug}</loc>" in body

    # Redirects and the healthcheck are not canonical URLs and must stay out.
    assert ".html" not in body
    assert "healthz" not in body


@pytest.mark.parametrize("path", page_paths())
def test_page_has_seo_head(client, path):
    html = client.get(path).get_data(as_text=True)
    assert f'<link rel="canonical" href="http://localhost{path}">' in html
    assert '<meta name="description" content="' in html
    assert '<meta property="og:image" content="http://localhost/static/' in html


def test_project_pages_have_their_own_description(client):
    descriptions = {
        client.get(f"/projects/{project.slug}")
        .get_data(as_text=True)
        .split('<meta name="description" content="')[1]
        .split('">')[0]
        for project in PROJECTS
    }
    assert len(descriptions) == len(PROJECTS), "project descriptions are not unique"


def test_404_is_not_indexable(client):
    html = client.get("/projects/nope").get_data(as_text=True)
    assert '<meta name="robots" content="noindex, follow">' in html
