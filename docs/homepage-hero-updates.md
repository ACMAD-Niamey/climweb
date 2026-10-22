# Homepage hero carousel

In Automatic mode, the meteorological homepage hero rotates through four
editorial positions in this order:

1. the newest published news item;
2. El Niño in Africa;
3. Summer School.

In Manual mode, the chosen News and Event slides appear first, followed by the
enabled programme slides. El Niño and Summer School can be switched on or off.

Only live, public pages below the current homepage and in its locale are used.
If one of the programme pages is not available, that slide is omitted rather
than linking to a hard-coded or missing URL.

## Content sources

- **Latest news** uses the newest non-future-dated News page, including its
  title, post date and social/listing image.
- **El Niño** uses the newest Product Item below the dedicated **El Niño in
  Africa** page for its title, date and image, and links to the El Niño landing
  page. If no issue exists yet, the landing page itself is still shown.
- **Summer School** uses the featured edition, falling back to the newest
  edition. The edition supplies the title, start date and image, while the
  slide links to the Summer School landing page.

All titles, dates and images therefore remain editable through their source
pages in Wagtail.

## Dashboard

Open **Pages → Homepage → Hero Carousel**.

- **Automatic** (default) uses the newest eligible news item for the first
  slide.
- **Manual** provides separate selectors for one News page and one Event page.
  When both are selected, News appears first and Event second.
- **Show El Niño** and **Show Summer School** independently control whether
  those programme slides are included.
- **Slide order** is a drag-and-drop list containing News, Event, El Niño and
  Summer School. Reorder these entries to control the Manual-mode sequence.
  Empty selectors and unchecked programme switches are skipped without
  disturbing the remaining order.

Enabled programme slides are appended after the News/Event selections.
Multiple slides rotate every 7.5 seconds and expose arrows and indicators.
Rotation pauses during hover, keyboard focus, or while the browser tab is
hidden. Reduced-motion users navigate manually.

## Deployment

Apply migrations (`manage.py migrate`) and collect static assets
(`manage.py collectstatic --noinput`) using the normal deployment workflow.
Restart the application and invalidate the homepage cache if the previous
carousel persists.
