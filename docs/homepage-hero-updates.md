# Homepage hero: Latest Updates

The meteorological homepage's right-hand hero card rotates through up to three
updates. When a published monthly issue exists below the dedicated **El Niño in
Africa** page, that issue is always the first slide and links to the El Niño
landing page. The remaining positions use news and events. Product imports and
the separate featured-products section are unchanged. The lower Latest Updates
section is also unchanged.

## Dashboard

Open **Pages → Homepage → Hero Latest Updates** and select:

- **Automatic** (default): the nearest upcoming/ongoing event first, then newest
  news by post date. Remaining spaces are filled with additional upcoming events
  if there is insufficient news. Finished events and future-dated news are excluded.
  Single-day events remain eligible throughout their start date in the site's timezone.
- **Manual**: select and reorder up to three news/event pages. An empty selection
  hides the news/event portion of the card; the El Niño bulletin still appears
  when one has been published. Past events may be deliberately selected in this mode.

Save and publish the homepage to apply configuration changes. Titles,
dates and images are inherited from the source pages; edit and publish those pages
to update their slides. Automatic mode does not require the source page's existing
“Is visible on homepage” flag; that flag continues to govern the separate lower feed.

Both modes only use live, public pages beneath this homepage in its locale. Private
pages (including pages below a restricted parent), drafts and pages from another
homepage are excluded. Removing an item or unpublishing it does not cause manual
mode to select a replacement automatically.

Missing images use a branded ACMAD fallback. Multiple slides rotate every 7.5
seconds, with arrows and indicators. There is no heading above the card, excerpt,
or pause/play button. Rotation pauses during hover, keyboard focus or when the tab
is hidden; reduced-motion users navigate manually without automatic rotation.
A single slide has no carousel controls. With no eligible updates or published
El Niño bulletin the card is hidden.

## El Niño monthly bulletin workflow

The deployment bootstrap creates an editable **Products → El Niño in Africa**
page if it does not already exist. To publish a new edition, add a **Product
Item** below that page, set its effective date, add the bulletin document and an
optional cover thumbnail, then publish it. The newest dated live issue becomes
the featured bulletin on the landing page and the first homepage hero slide;
older issues move into the page archive automatically.

## Deployment

Apply migrations (`manage.py migrate`) and collect static assets
(`manage.py collectstatic --noinput`) using the normal deployment workflow. Restart
the application and invalidate the homepage cache if the previous layout persists.
Migration `home.0044` adds the configuration fields and defaults to Automatic.
Existing hero product selections are retained in the database for reversibility,
and now drive the rotating product links in the top utility navbar. Editors manage
their order under **Pages → Homepage → Utility Navbar Products**. Each link uses the
latest published item from its selected product family; leaving the selection empty
uses the three original significant-product defaults. The rotation pauses on hover
or keyboard focus and shows only its first item when reduced motion is requested.
