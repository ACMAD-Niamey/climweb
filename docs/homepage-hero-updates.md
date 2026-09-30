# Homepage hero carousel

The meteorological homepage hero rotates through four editorial positions in
this order:

1. the newest published news item;
2. El Niño in Africa;
3. the Heat Early Warning System (HeatEWS); and
4. Summer School.

Only live, public pages below the current homepage and in its locale are used.
If one of the programme pages is not available, that slide is omitted rather
than linking to a hard-coded or missing URL.

## Content sources

- **Latest news** uses the newest non-future-dated News page, including its
  title, post date and social/listing image.
- **El Niño** uses the newest Product Item below the dedicated **El Niño in
  Africa** page for its title, date and image, and links to the El Niño landing
  page. If no issue exists yet, the landing page itself is still shown.
- **HeatEWS** resolves the **Heat and Thermal Stress** product by its stable
  `heat-and-thermal-stress` slug. Its newest issue supplies the date and image,
  while the slide links to the product landing page.
- **Summer School** uses the featured edition, falling back to the newest
  edition. The edition supplies the title, start date and image, while the
  slide links to the Summer School landing page.

All titles, dates and images therefore remain editable through their source
pages in Wagtail.

## Dashboard

Open **Pages → Homepage → Hero Carousel**.

- **Automatic** (default) uses the newest eligible news item for the first
  slide.
- **Manual** lets an editor choose one news or event page for the first slide.
  Leaving it empty shows only the three programme slides.

The El Niño, HeatEWS and Summer School slides are appended automatically in
both modes. Multiple slides rotate every 7.5 seconds and expose arrows and
indicators. Rotation pauses during hover, keyboard focus, or while the browser
tab is hidden. Reduced-motion users navigate manually.

## Deployment

Apply migrations (`manage.py migrate`) and collect static assets
(`manage.py collectstatic --noinput`) using the normal deployment workflow.
Restart the application and invalidate the homepage cache if the previous
carousel persists.
