"""Smoke tests: every page renders and every asset it points at exists."""

import re
from pathlib import Path

import pytest

from app import PROJECTS, app

STATIC_ROOT = Path(app.root_path) / "static"
ASSET_PATTERN = re.compile(r'(?:src|href)\s*=\s*"(/static/[^"]+)"')


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def page_paths():
    return ["/"] + [f"/projects/{project.slug}" for project in PROJECTS]


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
        assert f'href = "/projects/{project.slug}"' in html


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
