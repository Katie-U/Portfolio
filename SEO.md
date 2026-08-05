# SEO

How this site is set up for Google, what each change does, and what to do next.

Two things to be honest about up front:

- A five-page personal portfolio will never rank for competitive terms like
  "UX designer". That is not the goal. The goal is that **searching your name
  returns this site first**, that recruiters who paste the link get a decent
  preview, and that the pages load fast enough not to be penalised.
- SEO changes are slow. Expect days to weeks before Google reflects them, and
  ignore day-to-day movement in Search Console.

---

## Part 1 — Get Google to index the site

Nothing below matters until Google knows the site exists. Do these in order.

### 1. Pick one canonical domain and set `SITE_URL`

Decide whether the real address is the Railway subdomain
(`something.up.railway.app`) or a custom domain. Then in the Railway dashboard →
your service → **Variables**, add:

```
SITE_URL = https://your-real-domain.com
```

No trailing slash. Redeploy.

This matters more than it looks. Without it the app falls back to whatever
hostname the request came in on, so the same page is reachable — and
self-declares as canonical — at several addresses. Google treats those as
competing duplicates and splits the ranking signals between them instead of
pooling them on one URL.

If you use a custom domain, also make Railway redirect the `.up.railway.app`
address to it rather than serving both.

### 2. Verify the site in Google Search Console

<https://search.google.com/search-console> → **Add property**.

- Custom domain → choose **Domain** and add the TXT record it gives you at your
  registrar. This covers `http`, `https`, `www` and every subdomain at once.
- Railway subdomain only → you cannot add DNS records, so choose **URL prefix**
  and verify with the HTML tag method: it gives you a
  `<meta name="google-site-verification" content="...">` tag. Paste it into
  `templates/base.html` inside `<head>`, deploy, then click Verify. Leave the
  tag in place permanently.

### 3. Submit the sitemap

Search Console → **Sitemaps** → enter `sitemap.xml` → Submit.

Confirm it looks right first by visiting `https://your-domain/sitemap.xml`. It
should list the home page and all five project pages as absolute URLs, and it
regenerates itself from `PROJECTS` in `app.py`, so adding a project never leaves
it stale.

### 4. Request indexing for the home page

Search Console → **URL Inspection** → paste the home page URL → **Request
indexing**. This usually gets one page crawled within a day or two instead of
waiting for a natural crawl. You get a small daily quota, so spend it on the
home page and any project page you care most about.

### 5. Get at least one real link pointing at the site

This is the single highest-impact thing on this list and the only one that is
not a code change. Google discovers and trusts pages largely through links.

- LinkedIn profile → Contact info → Website. (LinkedIn marks outbound links
  `nofollow`, so it passes little ranking weight directly, but it *is* how Google
  and recruiters find the site.)
- GitHub profile README and the profile's website field.
- Your CMU MHCI cohort or program page, if it lists student sites.
- Any project write-up, class page, or organisation that already mentions you.

Five real links from places like these beat any amount of on-page tweaking.

### 6. Check it worked

After a week, search `site:your-domain.com` on Google. Every page should appear.
If a page is missing, run it through URL Inspection to see the reason.

---

## Part 2 — What was changed, file by file

### `app.py`

| Added | Why |
| --- | --- |
| `SITE_URL` env var + `site_url()` / `absolute_url()` | Canonical tags, Open Graph tags and sitemaps all require absolute URLs. Falls back to the request host so local dev still works. |
| `description` field on `Project` | Each project page needs its own meta description. Duplicate descriptions across pages are a wasted signal and Google usually rewrites them. |
| `seo_defaults()` context processor | Supplies `canonical_url`, `page_description`, `page_image`, `site_name` and `owner_name` to every template, so `base.html` never has to be edited per page. |
| `/robots.txt` route | Tells crawlers what to index, and points them at the sitemap. |
| `/sitemap.xml` route | Lists every canonical URL. Built from `PROJECTS`, so it cannot drift. Legacy `.html` redirects and `/healthz` are deliberately excluded — a sitemap should only ever contain canonical, indexable URLs. |

The `project()` route now passes that project's own `description` and thumbnail
into the template, overriding the site-wide defaults.

### `templates/base.html` — the `<head>`

Every change here applies to all six pages at once.

- **`<title>{% block title %}{% endblock %} | Katie Ulinski`** — the title tag is
  still the strongest on-page ranking signal, and it is the blue headline in
  results. Appending the name to every page means any page can win a name
  search. Keep titles under ~60 characters or Google truncates them.
- **`<meta name="description">`** — not a ranking factor, but it is the grey
  snippet under the headline, so it decides whether anyone clicks. Aim for
  150–160 characters.
- **`<meta name="author">`** — minor, reinforces the name association.
- **`<link rel="canonical">`** — declares the one true URL for the page. This is
  what stops `?fbclid=...` tracking parameters, the Railway subdomain and a
  custom domain from being treated as three separate duplicate pages.
- **Open Graph tags** (`og:title`, `og:description`, `og:image`, `og:url`,
  `og:type`, `og:site_name`) — control the preview card when the link is pasted
  into LinkedIn, Slack, iMessage, Discord or Teams. Without them those apps show
  a bare URL. Not a Google ranking factor, but it directly affects whether a
  recruiter clicks.
- **`<meta name="twitter:card" content="summary_large_image">`** — makes that
  preview a large image rather than a thumbnail.
- **`{% block structured_data %}`** — a hook so individual pages can add JSON-LD.
- **Favicon left as PNG** — Safari still will not render a WebP favicon.
- **Nav logo `alt`** changed from `"Home"` to the owner's name — this image is
  inside the link to the home page, so its alt text acts as that link's anchor
  text.

### `templates/index.html` — the home page

- **Title** changed from `Portfolio` to
  `UX Research & Interaction Design Portfolio` — "Portfolio" alone describes
  nothing and matches no realistic search.
- **JSON-LD `Person` schema** — machine-readable statement of who the site is
  about: name, job title, both universities, and the LinkedIn profile under
  `sameAs`. This is what Google reads when deciding whether a name search refers
  to a real person it can build a knowledge panel for.
- **`rel="me"` on the LinkedIn link** — the standard way to assert "this other
  profile is also me", reinforcing the `sameAs` claim above.
- **Hero image**: `alt=""` → `alt="Portrait of Katie Ulinski"`, plus
  `fetchpriority="high"` and `decoding="async"`. The hero is the largest element
  above the fold, so it is what Google measures for Largest Contentful Paint, one
  of the Core Web Vitals. It must never be lazy-loaded.
- **Section photos**: `alt=""` → real descriptions. Empty alt means "decorative,
  ignore me" to both screen readers and image search; these are real photographs
  of real work.
- **`loading="lazy"` on everything below the fold** — the project thumbnails and
  the two section photos are not fetched until the user scrolls near them.

### `templates/projects/*.html` — the five project pages

- **`loading="lazy" decoding="async"`** on every image except the first on each
  page. The first is potentially the LCP element, so it stays eager.
- **Videos** (`capstone.html`, `modeler.html`) now use
  `preload="none"` with a `poster` image, and point at `static/video-web/`.
  Previously the browser began pulling a 43 MB video on page load; now it fetches
  a ~40 KB poster frame and nothing else until someone presses play.
- A text fallback with a download link was added inside each `<video>` element,
  for browsers that cannot play it.
- Each page's meta description now comes from its `Project.description` in
  `app.py`, so all five are distinct.

### `templates/404.html`

- **`<meta name="robots" content="noindex, follow">`** — every unknown URL renders
  this same page. Without `noindex`, Google can index dozens of dead URLs all
  showing identical content, which is exactly the thin-duplicate-content pattern
  it penalises. `follow` still lets it crawl the link back to the home page.

### `templates/robots.txt` and `templates/sitemap.xml`

New files, rendered by the routes described above. `robots.txt` allows
everything except `/healthz` (infrastructure, not content) and advertises the
sitemap URL — many crawlers find a sitemap that way without it ever being
submitted.

### Images and video

Not SEO tags, but page speed is a ranking factor and this was by far the biggest
problem on the site.

| | before | after |
| --- | --- | --- |
| Images | 50 MB | 3.1 MB (−94%) |
| Video | 46 MB | 2.3 MB (−95%) |

The home page alone was pulling roughly 31 MB of images; `hero.jpg` was a 15 MB,
4000px-wide file being displayed at a few hundred pixels. See the README for how
to re-run the conversion scripts.

---

## Part 3 — What is still worth doing

Roughly in order of impact.

### 1. Make the site responsive (the big one)

`home-page.css` and `project-page.css` contain **no media queries**, and
`base.html` has no `<meta name="viewport">` tag. On a phone the page renders at
desktop width and gets scaled down, so text is tiny.

This matters because Google uses **mobile-first indexing**: it crawls and ranks
the site as a phone sees it, not as your laptop does. Right now Google's
Mobile-Friendly Test will fail on "viewport not set".

Do not just add the viewport tag on its own — without responsive CSS it makes
things *worse*, because content then overflows horizontally instead of being
neatly scaled down. The two go together:

1. Add `<meta name="viewport" content="width=device-width, initial-scale=1">`.
2. Add media queries that stack `.aboveTheFold`, `.undergraduate` and
   `.graduate` into a single column below ~768px.
3. Replace the fixed pixel widths and heights on images with
   `max-width: 100%; height: auto`.
4. Verify with Chrome DevTools device mode and PageSpeed Insights.

This is a contained CSS job and the single largest remaining SEO win.

### 2. Give images explicit width and height

Most `<img>` tags set only one dimension. When the browser does not know an
image's aspect ratio ahead of time, the page jumps as images load — that is
Cumulative Layout Shift, another Core Web Vital. Setting both `width` and
`height` (as HTML attributes, with CSS handling the actual display size) reserves
the space in advance. Do this as part of the responsive pass, since the values
depend on the new layout.

### 3. Write more text

Google ranks text. The project pages are reasonable; the home page is short and
the "About Me" section is commented out in `index.html`. Finishing and enabling
that section adds the natural place for the phrases someone would actually
search: the degree name, the universities, the city, the kind of work you want.

### 4. Add `BreadcrumbList` structured data to project pages

Makes results show `Portfolio › Modeler` instead of a raw URL. Small, cheap,
purely cosmetic in results — worth doing after the above.

### 5. Run PageSpeed Insights and fix what it flags

<https://pagespeed.web.dev/> — run it on the live URL after deploying. The image
and video work should already put the desktop score high; mobile will stay
capped until item 1 is done.

### 6. Check Search Console monthly

**Performance** shows which queries surface the site. **Pages** shows anything
Google refused to index and why. That is the whole maintenance loop.

---

## Things deliberately *not* done

- **Keyword stuffing / a keywords meta tag.** Google has ignored
  `<meta name="keywords">` since 2009.
- **Submitting to search engine directories.** Worthless, and the paid ones are
  scams.
- **`changefreq` and `priority` in the sitemap.** Google ignores both.
- **`lastmod` in the sitemap.** Git does not preserve file modification times, so
  a fresh clone would report every page as changed today. Google discounts
  `lastmod` it finds to be inaccurate, so an absent value beats a wrong one.
