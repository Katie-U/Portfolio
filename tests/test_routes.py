"""Smoke tests: every page renders and every asset it points at exists."""

import re
from pathlib import Path

import pytest

import app as app_module
from app import PROJECTS, app

STATIC_ROOT = Path(app.root_path) / "static"
ASSET_PATTERN = re.compile(r'(?:src|href|poster)\s*=\s*"(/static/[^"]+)"')

VALID_SUBMISSION = {
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "subject": "Hello",
    "message": "I liked your capstone project.",
}


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def sent(monkeypatch):
    """Configure the contact form and capture what it would have emailed.

    Resend is never called: the fixture replaces the send helper, so the tests
    exercise routing and validation without needing an API key or a network.
    """
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setattr(app_module, "CONTACT_TO_ADDRESS", "katie@example.com")

    captured = []
    monkeypatch.setattr(app_module, "send_contact_email", captured.append)
    return captured


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


def test_contact_page_renders_an_empty_form(client):
    html = client.get("/contact").get_data(as_text=True)
    assert html.count('value = ""') == 3, "fields should start empty"
    assert 'name = "website"' in html, "honeypot field is missing"


def test_contact_form_sends_the_submission(client, sent):
    response = client.post("/contact", json=VALID_SUBMISSION)

    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert sent == [VALID_SUBMISSION]


def test_contact_form_reports_missing_fields(client, sent):
    response = client.post("/contact", json={"name": "Ada"})

    assert response.status_code == 400
    assert set(response.get_json()["errors"]) == {"email", "subject", "message"}
    assert sent == []


@pytest.mark.parametrize("email", ["not-an-email", "ada@example", "ada @example.com"])
def test_contact_form_rejects_bad_addresses(client, sent, email):
    response = client.post("/contact", json={**VALID_SUBMISSION, "email": email})

    assert response.status_code == 400
    assert "email" in response.get_json()["errors"]
    assert sent == []


def test_contact_form_rejects_overlong_fields(client, sent):
    response = client.post("/contact", json={**VALID_SUBMISSION, "name": "a" * 101})

    assert response.status_code == 400
    assert "name" in response.get_json()["errors"]
    assert sent == []


def test_contact_form_drops_honeypot_submissions(client, sent):
    response = client.post("/contact", json={**VALID_SUBMISSION, "website": "spam.biz"})

    # Looks like success to the bot, but nothing is sent.
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert sent == []


def test_contact_form_reports_when_unconfigured(client, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    response = client.post("/contact", json=VALID_SUBMISSION)

    assert response.status_code == 503
    assert response.get_json()["ok"] is False


def test_contact_form_survives_a_resend_failure(client, sent, monkeypatch):
    def explode(_values):
        raise RuntimeError("Resend is down")

    monkeypatch.setattr(app_module, "send_contact_email", explode)

    response = client.post("/contact", json=VALID_SUBMISSION)

    assert response.status_code == 502
    assert response.get_json()["ok"] is False


def test_contact_form_works_without_javascript(client, sent):
    """A plain form post gets the page back, not a JSON blob."""
    response = client.post("/contact", data=VALID_SUBMISSION)

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert "Your message is on its way" in response.get_data(as_text=True)
    assert sent == [VALID_SUBMISSION]


def test_failed_form_post_keeps_what_was_typed(client, sent):
    response = client.post("/contact", data={**VALID_SUBMISSION, "email": "nope"})
    html = response.get_data(as_text=True)

    assert response.status_code == 400
    assert 'value = "Ada Lovelace"' in html
    assert "I liked your capstone project." in html
