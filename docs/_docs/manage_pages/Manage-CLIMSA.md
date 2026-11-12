# Manage the CLIMSA Programme Site

CLIMSA is a Wagtail programme site within the shared ClimWeb deployment. It has a dedicated homepage, About page,
programme navigation, curated outputs and content, and optional routing through `climsa.acmad.org`.

## Page types and hierarchy

```text
Main ACMAD Home Page
└── CLIMSA Home Page (maximum one)
    ├── CLIMSA About Page (maximum one per home)
    └── Flex Pages for additional programme content
```

Do not move the CLIMSA home outside the main homepage without technical review. Its parent restrictions and Site root
assume this hierarchy.

## Create or reconcile the site

An authorized operator can create the missing home/About pages and reconcile the Wagtail Site record:

```bash
python manage.py configure_climsa_subdomain --help
python manage.py configure_climsa_subdomain --create
```

The default hostname is `climsa.acmad.org` on port 443. The command may also select existing images named for the CLIMSA
and programme-partner logos. Review those images rather than assuming the filename guarantees correct branding.

The command does not configure DNS, nginx, or certificates. Follow the Subdomain Deployment and TLS guides.

## Homepage editing

Open the CLIMSA Home Page and maintain these sections:

### Brand and hero

- CLIMSA logo;
- hero image;
- programme kicker;
- hero heading;
- concise description.

Use approved logos with accessible titles and sufficient resolution. Confirm mobile crop and contrast.

### Programme introduction and outputs

Maintain the introduction heading, summary, programme-partners logo, and up to six programme-output blocks. Keep output
names and numbering consistent with the approved programme framework.

### Navigation destinations

Select the canonical About, Activities, Products, News, Publications, and Events pages. A missing/unpublished target can
remove or break a programme navigation item. After moving or replacing a page, update the chooser rather than relying on
an old URL.

### Curated content

Select up to seven products and up to six items each for news, events, and publications. Only live selected pages are
shown. Selection does not publish a draft item.

Review each item's programme relevance, language metadata, image, date, and destination before featuring it.

## About page

The About page contains:

- an optional page-specific hero;
- programme overview;
- five project outputs;
- programme factsheet heading, description, and URL.

Validate the factsheet URL and certificate before publication. Prefer an ACMAD-controlled document where licensing and
governance allow; record the external owner when an external URL is required.

## Programme navigation

Maintain the CLIMSA menu in **Settings → Navigation settings** where the candidate release provides it. Test:

- the programme homepage;
- About and at least one Flex page;
- all curated content destinations;
- both the main ACMAD route and dedicated CLIMSA hostname;
- mobile navigation and search.

## Content migration procedure

Use `migration/climsa/current-site-audit.md` as the source audit, then maintain a migration ledger with expected, imported,
rejected, duplicate, and missing records. Preserve source URLs and redirect decisions. Do not import demo/theme content
identified by the audit.

Before acceptance, reconcile pages, news, events, publications, products, documents, images, partner assets, menus, and
redirects. Missing source documents must remain explicit outstanding actions.

## Release and acceptance

The CLIMSA implementation exists on divergent feature histories. Before deploying:

1. Select the canonical branch and review unique commits.
2. Resolve migration numbering and shared navigation changes.
3. Run tests and migrations on a production-like copy.
4. Configure DNS/TLS/nginx only for the accepted release.
5. Run the configuration command and verify the Wagtail Site root.
6. Complete content and responsive acceptance with the programme owner.

## Acceptance checklist

- [ ] Correct canonical CLIMSA branch/release selected.
- [ ] Homepage and About page types/hierarchy are correct.
- [ ] Official logos, output wording, and factsheet are approved.
- [ ] Every navigation chooser points to a live canonical page.
- [ ] Curated products/news/events/publications are relevant and live.
- [ ] Migration ledger and redirects are reconciled.
- [ ] Main-site and dedicated-host routing are correct.
- [ ] DNS, TLS, nginx, mobile, accessibility, and broken links are verified.
- [ ] Programme editor and technical owner are named.
