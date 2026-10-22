# CLIMSA current website audit

Audit date: 2026-10-05
Source: <https://climsa.acmad.org/>

## Purpose

This audit defines the source material and migration boundary for rebuilding the
CLIMSA website in ClimWeb. It inventories the public WordPress site, identifies
content that belongs to CLIMSA, separates theme/demo residue, and records risks
that must be resolved before importing documents and product links.

This is a source-content audit, not approval of the current copy or visual design.

## Agreed design direction

- Preserve the current primary menu labels and order.
- Use the ACMAD logo on the left, the main menu in the centre, and the CLIMSA
  logo on the right.
- Keep the African Union Commission, European Union, and OACPS partner marks in
  the header as a secondary logo group.
- Move search into the utility navigation.
- Use a CLIMSA-scoped blue palette while retaining the ACMAD/ClimWeb component
  language and typography.
- Prefer flat surfaces, borders, spacing, and restrained colour changes. Avoid
  unnecessary shadows and gradients.

The current partner banner is one 770 x 131 composite image containing ACMAD,
the African Union Commission, the European Union, and OACPS. In the new header,
the ACMAD mark should be separated from that composite to avoid showing ACMAD
twice. The remaining three partner marks can retain their current visual grouping.

## Current navigation

The live desktop navigation has no dropdowns and contains exactly:

| Order | Label | Current destination |
|---:|---|---|
| 1 | Home | `/` |
| 2 | About Us | `/about/` |
| 3 | Activities | `/insurance-02/` |
| 4 | Products | `/portfolio-01/` |
| 5 | News | `/news/` |
| 6 | Publications | `/gallery/` |
| 7 | Events | `/event-page/` |

These labels should remain the CLIMSA navigation. The destinations should use
clean ClimWeb URLs, with permanent redirects from every legacy URL.

## Platform and public inventory

The current site is WordPress using Elementor, a Modins child theme, Slider
Revolution, WooCommerce, The Events Calendar, Contact Form 7, TablePress, and
several Elementor add-on packages.

Public endpoints reported the following content:

| Content type | Count | Migration interpretation |
|---|---:|---|
| WordPress pages | 73 | 31 English CLIMSA pages, 6 nominal language copies, and 36 demo/unrelated pages |
| Posts | 8 | 7 English news posts and 1 French post |
| Calendar events | 6 | Real event records, but with inherited demo slugs |
| Portfolio records | 11 | Publication/newsletter records; several use poor slugs |
| WooCommerce products | 9 | Fashion demo products; exclude completely |
| Media records | 268 | Images, SVGs, video and branding assets; audit before import |
| Venues | 7 | Five useful English venues plus translated/unused residue |
| Organizers | 2 | CLIMSA plus one demo organizer named Gary Jones |

At least 239 media records were publicly enumerable during the audit: 166 JPEG,
62 PNG, 7 SVG, and 4 MP4 files. The WordPress media endpoint reports 268 total,
so the importer must not assume that a single unauthenticated enumeration contains
the complete library.

## Keep: authoritative CLIMSA content

### Homepage

The homepage contains:

- A seven-slide hero/slider.
- A short programme introduction linking to About Us.
- Six project-output cards, Outputs 0 through 5.
- Seven featured products.
- Six latest-news cards.
- Five latest-event cards.
- The programme statement and ACMAD contact details in the footer.

The homepage is manually assembled and duplicates content from the Activities,
Products, News, and Events pages. In ClimWeb these sections should query their
canonical records instead of storing a second copy.

### About Us

`/about/` contains the programme overview, funding/context text, the five
programme outcomes, and a link to the programme factsheet. The French, Arabic,
and Portuguese About pages currently contain the same English body text; they
are copies, not translations.

### Activities

`/insurance-02/` is the Activities landing page. Its six cards represent:

| Output | Current detail page | Main content |
|---|---|---|
| 0 | `/climsa-steering-commitees/` | Continental steering committees and the third/fourth committee meetings |
| 1 | `/output-1/` | User-interface platforms and sector workshops |
| 2 | `/1400-2/` | Climate-service provision and related activities/deliverables |
| 3 | `/1427-2/` | Climate-data access, data centre, and service catalogue |
| 4 | `/output-4/` | Capacity-building activities and deliverables |
| 5 | `/output-5/` | Climate-informed decision-making activities and deliverables |

Supporting Output 1 and steering-committee pages include:

- Third and fourth ACMAD-CLIMSA Project Steering Committee meetings.
- Nile Basin Development Forum.
- Climate Services User Interface Platform workshop.
- UIP workshops for hydrology and infrastructure.
- 2023 Clim-Health Africa meeting.
- Continental and regional drought-monitoring/capacity-building workshop.

One Output 1 link incorrectly points to a WordPress administration URL and must
be replaced with the public Nile Basin page during migration.

### Products

The primary Products page currently presents seven static featured documents:

1. Characteristic of the Onset of the Agricultural Season over Africa,
   16–30 July 2024.
2. Seasonal Rainfall Outlook valid for JJA 2023.
3. Seasonal forecast of precipitation for May–June–July 2024.
4. El Niño 2023 impact over Southern Africa.
5. Flood risks in West and Central Africa.
6. ACMAD El Niño Impacts Information Note.
7. Prévision climatique saisonnière en Afrique centrale.

All seven currently point to document URLs that return 404. Their preview images
are available in the CLIMSA media library, but the source documents must be
recovered before the cards are republished.

### Output 3 service catalogue

Output 3 links to nine service pages:

| Service | Current state | Links/data |
|---|---|---|
| Long Range Forecasting | Substantial product table | Descriptive rows but no working file links in rendered content |
| Climate Monitoring | Populated | 8 THREDDS image/CSV links |
| Climate and Health | Populated product table | Download labels do not resolve to files in rendered content |
| Climate Change | Empty body | Requires source/reconstruction |
| Training ACMAD Service | Empty body | Requires source/reconstruction |
| Nowcasting | Substantial product table | Descriptive rows but no file links |
| Short Range Weather Forecast | Populated | 27 PNG links, including a duplicate |
| Weekly Weather Forecast | Populated product table | Download labels do not resolve to files in rendered content |
| Heat Wave | Very thin | 2 PNG links |

All 36 unique THREDDS/file-server links found in the authoritative content
returned HTTP 200 on the audit date. They are served over plain HTTP on port
8080, so the new HTTPS site should use a controlled proxy/importer or another
HTTPS-safe delivery strategy instead of embedding mixed-content URLs.

### News

The public site has eight posts:

- PRESAC-19: Development of Services for Climate Risk Resilience of Central
  African Socio-Economic Sectors.
- Online training workshop on seasonal climate prediction.
- Online user-engagement training on agricultural season onset.
- Special information on flooding in the Sahel.
- ACMAD hosts a joint UN mission to strengthen early warning and disaster-risk
  reduction.
- Global Flood Partnership Meeting.
- Consultation workshop for climate-services user platforms.
- A French drought-monitoring workshop post.

The French post currently appears in the English homepage/news listing. Language
filtering should be explicit in the new implementation.

### Publications

The sitemap exposes 11 portfolio records. The visible Publications landing page
shows six at a time. The meaningful records comprise:

- Monthly CLIMSA Newsletter, July–August 2022.
- Special COP26 newsletter.
- PRESAC 14.
- Monthly CLIMSA Newsletter, April–May–June 2023.
- Monthly CLIMSA Newsletter, February–March–April 2023.
- CLIMSA Newsletter, October–November–December 2022.
- Newsletter, October–November–December 2023.
- Newsletter, April–May–June 2024.
- ACMAD contribution to the climate-health nexus newsletter.
- Flood/inundation information records.

The route `/case/business-strategy/` displays a flood publication, demonstrating
that the portfolio slugs were inherited from demo content and cannot be treated
as authoritative titles.

### Events

Six archived event records exist:

| Event | Start | Venue | Current slug problem |
|---|---|---|---|
| PRESASS-11 | 2024-04-22 | Abuja | `architecture-week` |
| Fourth ACMAD-CLIMSA Steering Committee Meeting | 2024-05-28 | Addis Ababa | `designing-club-culture` |
| User-platform consultation workshop | 2024-07-23 | Douala | `nairobi-design-week` |
| Global Flood Partnership Meeting | 2024-07-24 | Nairobi | `architecture-club-meetup` |
| Online seasonal-climate workshop | 2024-09-02 | Online | `international-architecture-2023` |
| Agricultural season-onset user training | 2024-09-03 | Online | `festival-of-architecture-and-interior` |

The seasonal-climate workshop has an end date of 2025-09-07, which is likely a
data-entry error and should be confirmed before import.

## Exclude: theme and demo residue

Do not migrate the following even though WordPress exposes or indexes them:

- Duplicate home templates: Home 1, Home 3, Home 4, and Home 5.
- About Me, Pricing, Testimonials, Team, Get a Quote, and generic sample pages.
- News 02/03 and Portfolio 02/03 template variants.
- Insurance demo landing/detail pages, including car, life, home, health,
  business, fire, marriage, and travel insurance.
- Shop, cart, checkout, account, and duplicate WooCommerce system pages.
- All nine fashion WooCommerce products.
- The demo organizer `Gary Jones` and the unused New York venue.
- Elementor/header/footer templates and plugin-specific content records.

Leaving this material out is essential: 36 of the 73 public WordPress pages are
demo or unrelated content.

## Branding and header findings

Current desktop branding is arranged in two columns:

1. A large CLIMSA logo on the left.
2. A single partner banner on the right containing ACMAD, African Union
   Commission, European Union, and OACPS marks.

The main navigation sits on a separate full-width blue row below the logos. The
partner banner has an empty `alt` attribute, and the CLIMSA logo uses `Home` as
its alternative text. Both need meaningful accessible labels.

The new composition should use separate assets and responsive rules rather than
shrinking the 770-pixel composite banner. On small screens, the partner group can
move to a secondary row while ACMAD, the menu trigger, and CLIMSA remain legible.

## Link and document audit

Across the authoritative pages and posts, the rendered content contains 216
unique absolute URLs:

- 127 on `climsa.acmad.org`.
- 36 on the ACMAD THREDDS/file server.
- 35 on `acmad.org`.
- 4 invalid `localhost/climsa2` image links.
- 14 spread across CLIMSA.org, JRC, Google Maps/Forms, Zoom, the Nile Basin
  site, Eventleaf, and other ACMAD endpoints.

There are 76 plain-HTTP links. Four `localhost` image references occur on the
third steering-committee and drought/capacity-building pages and can never work
for public visitors.

### Documents

The authoritative content references 36 unique PDF/Excel documents. Checks made
after following redirects produced:

| Result | Count | Meaning |
|---|---:|---|
| HTTP 200 | 2 | PRESAC-19 agenda and concept note on the current ACMAD document service |
| HTTP 404 | 33 | Old `acmad.org/wp-content/uploads/2019/03/` files no longer available at their linked location |
| TLS verification failure | 1 | External CLIMSA factsheet uses a certificate that does not match `www.climsa.org` |

Document recovery is therefore a prerequisite for a faithful migration. Sources
should be checked in this order:

1. Existing ACMAD/CLIMSA WordPress backups and media archives.
2. Current ACMAD Wagtail documents/media.
3. Project team archives.
4. The old site only when a file still resolves.

No broken document should be imported as an active download button.

## Content-quality issues to correct during migration

- `Commitee`/`Commitees` should be `Committee`/`Committees`.
- `HEAT WAVEHEAT WAVE` is duplicated.
- `agriculcure` should be `agriculture`.
- Several service descriptions begin with stray text such as `IThe` or `IThis`.
- The displayed email is `contact@acmad.org`, but its link target is the
  placeholder `contact@example.com`.
- Generic numeric slugs include `/1400-2/`, `/1416-2/`, `/1427-2/`,
  `/1439-2/`, and `/1595-2/`.
- `/1416-2/` has no title and essentially no body content.
- Climate Change and Training service pages have empty bodies.
- Many cards repeat the same link twice because both image and text are linked.
- Event and portfolio URLs retain names from the purchased theme demo.
- News titles contain literal ellipses and inconsistent capitalization.
- Product/service data is mostly from 2021–2024 and must be presented as an
  archive unless a current feed replaces it.

Copy should be proofread while preserving programme meaning. Corrections should
not silently alter technical claims, dates, deliverables, or official event names.

## Language audit

The site exposes French, Arabic, and Portuguese versions of the homepage and
About page, but their bodies are identical English copies. Only one actual French
news post was found. There is no complete translated information architecture.

Migration should therefore distinguish between:

- content genuinely translated and ready to publish;
- English fallback content; and
- missing translations.

Publishing English copies as if they were Arabic, French, or Portuguese
translations should not be reproduced.

## URL and redirect requirements

Clean URLs should be created for every retained record. Examples:

- `/insurance-02/` -> `/activities/`
- `/portfolio-01/` -> `/products/`
- `/gallery/` -> `/publications/`
- `/event-page/` -> `/events/`
- `/1400-2/` -> `/activities/output-2/`
- `/1427-2/` -> `/activities/output-3/`
- `/1439-2/` -> `/services/long-range-forecasting/`
- `/heat-waveheat-wave/` -> `/services/heat-wave/`
- `/elementor-2404/` -> a title-derived PRESAC-19 news slug

The final redirect map must also include query-style links such as
`?page_id=586`, legacy event slugs, and portfolio `case` slugs. Demo routes should
return 404/410 rather than redirecting users into unrelated CLIMSA content.

## Recommended migration boundary

### Import

- The seven navigation destinations and their authoritative child records.
- Six programme outputs and supporting activity/meeting pages.
- Seven featured products once their documents are recovered.
- Nine Output 3 service pages, retaining empty pages as drafts until completed.
- Eight news posts.
- Eleven publication/portfolio records after document recovery and deduplication.
- Six archived events after correcting slugs and the questionable end date.
- Relevant branding, hero, card, gallery, and article media.
- ACMAD contact details and programme statement.

### Do not import

- WordPress theme/template pages and plugin configuration records.
- WooCommerce pages and fashion products.
- Insurance demo content.
- Placeholder contacts, localhost URLs, or broken download buttons.
- Fake language copies.

## Implementation prerequisites

Before building the full page set:

1. Recover the 33 missing ACMAD-hosted documents and the CLIMSA factsheet.
2. Confirm whether the nine service tables are historical archives or should be
   fed by a current catalogue/importer.
3. Confirm the seasonal-climate event end date.
4. Obtain separate official source files for ACMAD, AUC, EU, OACPS, and CLIMSA
   logos; avoid extracting them from the low-resolution composite banner.
5. Decide which languages have approved translations at launch.
6. Approve the legacy-to-clean redirect map.

## Proposed implementation sequence

1. Generalize the RCC section-navigation mechanism and add CLIMSA context.
2. Implement the flat CLIMSA header, utility search, partner branding, mobile
   header, and the existing seven-item navigation.
3. Create the CLIMSA homepage and canonical content models.
4. Import About and Outputs 0–5 with their child activity pages.
5. Import service tables and configure safe THREDDS delivery.
6. Recover/import products and publications.
7. Import news and events, then add redirects.
8. Run automated model, route, navigation, link, and local HTTP smoke tests.
9. Hand each completed feature group to the site owner for visual validation.

## Audit sources

- WordPress sitemap index and all exposed child sitemaps.
- Public WordPress REST endpoints for pages, posts, media, content types, venues,
  organizers, and products.
- The Events Calendar public REST endpoint, queried across 2020–2030.
- Rendered homepage and portfolio HTML for navigation, branding, and content not
  available through the WordPress REST API.
- Direct HTTP checks of all discovered document and THREDDS links.
