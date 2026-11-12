# Manage the ENSO Information Hub

The ENSO hub is implemented as the single `ElNinoPage` below the Product Index. It presents Africa-focused context,
ACMAD's response, the latest monthly bulletin, an archive, related content, and optional homepage promotion.

## Roles

- **Climate editor:** validates scientific wording and bulletin dates.
- **Web editor:** updates page copy, images, related content, and publication state.
- **Product operator:** maintains the bulletin importer/source and verifies new issues.
- **Publisher/reviewer:** approves scientifically and editorially sensitive changes.

## Create or reconcile the page

Only one ENSO page is permitted. Use the management command to seed missing baseline content:

```bash
python manage.py seed_el_nino_page --help
python manage.py seed_el_nino_page
```

Run it first in a non-production environment and review the resulting page, product category, and importer configuration.
Do not create a second generic product page for the same bulletin series.

## Edit the page

In **Pages → Products**, open the El Niño/ENSO page. Maintain:

- the standard product-page title, banner, introduction, image, and metadata;
- **El Niño in Africa** context;
- **What ACMAD is doing**;
- the monthly bulletin introduction;
- pagination and other inherited product settings where exposed.

Use terminology approved by the climate-services owner. Preview desktop and mobile layouts before publication.

## Publish a bulletin

Bulletins are `ProductItemPage` children of the ENSO page. The newest issue by product ordering becomes the featured
latest bulletin; the remainder form the archive.

For each issue:

1. Confirm the issue/effective date and validity period.
2. Use a clear title containing the period.
3. Attach the authoritative PDF through a document-product block.
4. Add an approved thumbnail or preview image where available.
5. Confirm the document opens and represents the stated period.
6. Preview the ENSO page and homepage before publishing.
7. Retain previous issues unless the climate owner authorizes withdrawal.

The hero download button uses the first document-product block on the latest issue. If it is missing, incorrectly ordered,
or unpublished, the button may not resolve to the intended bulletin.

## Related news, events, and partner activities

Use the page's supported related-content fields and standard News/Event pages. Confirm every external activity link has
an accountable source, useful title, suitable image, and valid destination. Do not copy third-party content without
permission; summarize and link to the source.

## Homepage carousel

Open **Pages → Homepage → Hero Carousel**:

- enable **Show El Niño**;
- add/reorder the El Niño item in manual mode if required;
- preview the slide title, image, link, and fallback behavior;
- verify the newest bulletin thumbnail does not replace the intended page image unexpectedly.

The carousel links to the ENSO landing page, not directly to an unreviewed external file.

## Import operations

Before enabling automatic bulletin imports:

1. Test the source connection.
2. Preview matching files and naming/date extraction.
3. Confirm destination category/page and duplicate behavior.
4. Perform one manual import.
5. Verify the issue page, document, thumbnail, date, and homepage presentation.
6. Enable a schedule only after the manual acceptance record is complete.

See the ACMAD Product Migrations and Product Importer guides for stop, retry, history, and source configuration.

## Acceptance checklist

- [ ] One live ENSO page exists below Products.
- [ ] Scientific copy has an identified reviewer and review date.
- [ ] Latest bulletin date, title, document, thumbnail, and link are correct.
- [ ] At least one archived issue is reachable when archives exist.
- [ ] Related news/events are relevant and live.
- [ ] Homepage visibility and ordering are intentional.
- [ ] Mobile pagination, image crops, and download behavior are verified.
- [ ] Importer source, owner, schedule, and failure escalation are recorded.

## Troubleshooting

- **Wrong bulletin featured:** review issue dates/order and publication state.
- **No download link:** ensure the latest issue contains a published document-product block.
- **No homepage slide:** confirm the page and latest issue are live/public and the homepage toggle/order permits ENSO.
- **Duplicate issue:** inspect importer provenance and date/name matching before deleting anything.
- **Stale image or copy:** preview the page, confirm the published revision, then follow the approved cache-clearing process.
