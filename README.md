# Portfolio

Katie Ulinski's portfolio site, served by a small Flask app and deployed on Railway.

## Layout

```
app.py                  Flask app: routes and the project registry
Procfile                Railway/Heroku start command (gunicorn)
pyproject.toml          Dependencies, managed by uv
uv.lock                 Pinned dependency versions
templates/
  base.html             Shared <head> and nav
  index.html            Home page
  404.html              Not-found page
  projects/*.html       One template per project page
static/
  css/                  home-page.css, project-page.css
  js/                   main.js
  images/               Photos, logos, prototypes
  video/                Project videos
tests/                  Smoke tests for routes and asset links
```

Project cards on the home page are generated from the `PROJECTS` list in `app.py`.
To add a project: add a `Project(...)` entry there and create the matching
template under `templates/projects/`.

## Running locally

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python app.py
```

The site is then at <http://127.0.0.1:5000>.

## Tests

```bash
uv run pytest
```

The tests render every page and assert that every `/static/...` URL they
reference exists on disk, so a broken image or stylesheet path fails the build.

## Deploying to Railway

Railway detects `uv.lock` and installs with uv, then runs the `Procfile`
command. No extra configuration is needed; `$PORT` is supplied by Railway.

A healthcheck endpoint is available at `/healthz`.

## Notes

- Old flat URLs (`/project-description-modeler.html`, etc.) 301-redirect to the
  new `/projects/<slug>` URLs.
- `gunicorn` does not run on Windows. Local development uses the Flask dev
  server via `uv run python app.py`; gunicorn is only used on Railway.
