# Portfolio

Katie Ulinski's portfolio site, served by a small Flask app and deployed on Railway.

## Layout

```
app.py                  Flask app: routes, project registry, SEO helpers
Procfile                Railway/Heroku start command (gunicorn)
pyproject.toml          Dependencies, managed by uv
uv.lock                 Pinned dependency versions
SEO.md                  What was done for search ranking, and what to do next
scripts/
  convert_images.py     Originals -> compressed WebP
  compress_videos.py    Originals -> web-sized MP4 + poster frame
templates/
  base.html             Shared <head> (meta tags, Open Graph) and nav
  index.html            Home page
  404.html              Not-found page
  projects/*.html       One template per project page
  robots.txt            Rendered by the /robots.txt route
  sitemap.xml           Rendered by the /sitemap.xml route
static/
  css/                  home-page.css, project-page.css
  js/                   main.js
  images/               Full-size originals (NOT in git, see below)
  images-webp/          Compressed images -- this is what the site serves
  video/                Full-size originals (NOT in git, see below)
  video-web/            Compressed video + posters -- this is what the site serves
tests/                  Smoke tests for routes, asset links and SEO tags
```

Project cards on the home page are generated from the `PROJECTS` list in `app.py`.
To add a project: add a `Project(...)` entry there and create the matching
template under `templates/projects/`. The sitemap picks it up automatically.

## Running locally

Requires [uv](https://docs.astral.sh/uv/). It manages the Python version and the
virtual environment for you -- there is no need to create one by hand.

```bash
# One time: install uv (Windows)
winget install --id=astral-sh.uv

# Install dependencies into .venv (creates it if missing)
uv sync

# Start the dev server
uv run python app.py
```

The site is then at <http://127.0.0.1:5000>. The dev server reloads on save, so
leave it running while you edit templates.

To run on a different port:

```bash
PORT=8000 uv run python app.py        # bash
$env:PORT=8000; uv run python app.py  # PowerShell
```

`gunicorn` (in the `Procfile`) does not run on Windows. It is only used on
Railway; locally always use `uv run python app.py`.

## Saving and publishing a change

The everyday loop, from an edited file to a live site:

```bash
# 1. See what you changed
git status

# 2. If you added or replaced anything in static/images/ or static/video/,
#    regenerate the compressed copies first (see "Images and video" below)
uv run --group images python scripts/convert_images.py
uv run python scripts/compress_videos.py

# 3. Make sure nothing is broken
uv run pytest

# 4. Stage everything you changed
git add -A

# 5. Commit with a message describing the change
git commit -m "Shorten the capstone write-up"

# 6. Send it to GitHub
git push
```

Then **open Railway and press Deploy** — pushes do not deploy on their own here.
See [Pushes do not auto-deploy](#pushes-do-not-auto-deploy) for why and how to
fix it permanently.

### Useful variations

```bash
git add templates/index.html          # stage one file instead of everything
git diff                              # review unstaged changes before adding
git diff --cached                     # review what is already staged
git restore templates/index.html      # throw away edits to one file
git log --oneline -10                 # recent history
```

### Working on a branch instead

Safer for anything larger than a typo, and it is how changes have been merged
into this repo before:

```bash
git checkout -b shorter-capstone-text   # start a branch off main
# ...edit, test, add, commit as above...
git push -u origin shorter-capstone-text
```

Then open a pull request on GitHub and merge it. Afterwards:

```bash
git checkout main
git pull
```

### Two things that catch people out here

- **`git add` silently ignores the originals.** `static/images/` and
  `static/video/` are gitignored, so `git add static/images/new-photo.jpg` does
  nothing at all — no error, no warning. Only the compressed copies in
  `static/images-webp/` and `static/video-web/` get committed, which is why
  step 2 above has to happen *before* step 4. If a new image is missing from the
  live site, this is almost always why.
- **Always `git pull` before starting.** This repo has more than one person
  pushing to it, and pulling first avoids merge conflicts later.

## Tests

```bash
uv run pytest
```

The tests render every page and assert that every `/static/...` URL they
reference exists on disk, so a broken image, video or stylesheet path fails the
build. They also check the canonical tag, per-page descriptions, `robots.txt`
and `sitemap.xml`.

## Images and video

The originals were straight off a camera and a screen recorder: about 96 MB
between them, for a site whose largest image renders at 700px wide. Everything
is now served from compressed copies.

|        | originals                   | served                        |
| ------ | --------------------------- | ----------------------------- |
| Images | `static/images/` — 50 MB    | `static/images-webp/` — 3.1 MB |
| Video  | `static/video/` — 46 MB     | `static/video-web/` — 2.3 MB   |

**The originals are not in git.** They are gitignored, because Railway would
otherwise redeploy 96 MB of files that no page ever requests. Keep them on your
machine and backed up somewhere else — a fresh `git clone` will not have them in
the working tree, and without them the scripts below cannot be re-run.

They do remain in git history, so a copy can be pulled back out of the commit
before they were untracked:

```bash
git checkout <that-commit> -- static/images static/video
```

Because history still holds them, this does not shrink the size of a clone —
only what Railway deploys. (The one exception to the ignore rule is
`static/images/home-icon.png`, the favicon, which stays tracked: Safari refuses
to render a WebP favicon.)

The compressed folders **are** committed, because nothing on Railway runs these
scripts during a deploy.

### Re-running the compression

After adding or replacing an original, regenerate the served copies and commit
the result:

```bash
# Images: needs the optional "images" dependency group (Pillow)
uv run --group images python scripts/convert_images.py --dry-run
uv run --group images python scripts/convert_images.py

# Video: needs ffmpeg on PATH (winget install Gyan.FFmpeg)
uv run python scripts/compress_videos.py --dry-run
uv run python scripts/compress_videos.py
```

Both scripts read from the originals folder, write to the served folder, never
modify the originals, and skip files whose output is already up to date (pass
`--force` to override). `convert_images.py` caps the longest edge at 2000px;
`compress_videos.py` caps width at 1280px and writes a `.webp` poster frame next
to each video, so a page costs nothing until someone presses play.

Useful flags: `--quality` / `--max-edge` for images, `--crf` / `--preset` /
`--max-width` for video. Lower CRF means better quality and a bigger file.

Pillow lives in a non-default dependency group so Railway does not install it at
runtime, which is why the image script needs `--group images`.

## Deploying to Railway

Railway detects `uv.lock`, installs with uv, then runs the `Procfile` command.
`$PORT` is supplied by Railway. A healthcheck endpoint is at `/healthz`.

Set one environment variable in the Railway dashboard:

```
SITE_URL = https://your-real-domain.com
```

Without it the canonical tags, Open Graph URLs and `sitemap.xml` fall back to
whichever hostname the request arrived on. That works, but it lets the Railway
subdomain and a custom domain each claim to be canonical, which splits your
search ranking between them. See `SEO.md`.

### Pushes do not auto-deploy

Railway shows **"GitHub Repo not found"** under *Branch connected to production*,
so pushes to `Katie-U/Portfolio` never reach it and every deploy has to be
triggered by hand.

The cause is permissions, not configuration. Railway watches a repo through the
Railway GitHub App, and only someone with admin rights on that repo can install
the app and create the push webhook. The Railway account here is connected to a
GitHub account that does not own `Katie-U/Portfolio`, so Railway can neither see
the repo nor subscribe to its pushes.

Three ways out, least disruptive first:

1. **Have the repo owner authorise it.** The owner of `Katie-U/Portfolio` goes to
   <https://github.com/settings/installations>, installs or configures the
   *Railway* app, and grants it access to the `Portfolio` repository.
   Auto-deploy then starts working with no change on this end. (If the owner
   instead adds you as an admin collaborator, you can install it yourself.)
2. **Deploy from the CLI.** No GitHub involvement at all — this uploads the
   working directory straight to Railway:
   ```bash
   npm install -g @railway/cli
   railway login
   railway link          # pick the existing project, once
   railway up            # deploy the current directory
   ```
   This deploys what is on disk, not what is on GitHub, so still commit and push
   or the two drift apart.
3. **Point Railway at your own fork.** Fork the repo to your account, connect
   Railway to the fork (you have admin there, so the app installs cleanly), and
   open PRs upstream. Deploys then follow your fork rather than the original.

Until one of those is done, hit **Deploy** in the Railway dashboard after each
push.

## Notes

- Old flat URLs (`/project-description-modeler.html`, etc.) 301-redirect to the
  new `/projects/<slug>` URLs.
- `robots.txt` and `sitemap.xml` are generated by Flask routes rather than being
  static files, so the sitemap cannot go stale relative to `PROJECTS`.
