# Manage News and Media Content

This guide covers ACMAD news articles, article-body video, quotation content, image/video galleries, external links, and
media governance. Some capabilities exist only on later feature branches; confirm the candidate release before training
editors or creating migration-dependent content.

## Article workflow

1. Create or open the News page below the correct news index.
2. Enter title, date, category/tags, summary, banner/thumbnail, and body.
3. Add related services, programmes, or external links where supported.
4. Add videos and galleries using structured blocks, not pasted iframe/HTML code.
5. Preview desktop and mobile layouts.
6. Submit through the configured editorial workflow and publish only after approval.

## Uploaded and hosted video

Later news blocks support:

- uploaded video documents such as MP4/WebM;
- hosted video URLs such as YouTube or Vimeo;
- optional preview/poster images;
- video items within mosaic galleries;
- video blocks following the article body.

Before publishing a video:

- confirm rights, consent, and intended audience;
- use the structured hosted-video field rather than arbitrary embed HTML;
- add a meaningful title/caption and poster where supported;
- provide captions/transcript or a documented remediation action;
- test playback without privileged cookies;
- check file size, format, bandwidth, and mobile behavior;
- do not upload confidential meeting recordings.

External hosts can remove or restrict content. Record the source owner and review date.

## Quotations and reviews

Use approved quotation/review blocks. Record the speaker/source, role or context, permission, and original evidence.
Correct only obvious typographical issues without changing meaning. Do not publish private feedback as a testimonial
without consent.

## Galleries

For mosaic galleries:

- lead with the most representative item;
- avoid near-duplicates;
- provide useful image titles/alt text and captions;
- preserve photographer/source credit where required;
- mix image and video only when the resulting narrative remains clear;
- preview different item counts and aspect ratios;
- confirm every media item is included in backup and migration plans.

## Migration and release safety

News video/gallery changes introduce migrations and template changes on `summer-school-enhancement`. Before integrating:

1. Review the `news` migration graph against `origin/develop`.
2. Test existing articles with empty, image-only, and mixed-media galleries.
3. Test old revisions and page preview.
4. Validate uploaded document types and response headers.
5. Confirm rollback/migration compatibility before production deployment.

Do not create production content that depends on these fields until the release containing them is accepted.

## Accessibility and performance

- Provide text alternatives for meaningful images.
- Caption or transcribe speech content.
- Avoid autoplay with sound.
- Do not encode essential information only inside an image or video.
- Compress media before upload and use appropriate poster images.
- Test keyboard operation, focus, controls, contrast, and reduced-motion behavior.

## Acceptance checklist

- [ ] Candidate release supports every block used by the article.
- [ ] Editorial approval and media rights are recorded.
- [ ] Titles, dates, summaries, tags, and related content are accurate.
- [ ] Videos play on supported browsers and have captions/transcript plans.
- [ ] Gallery crops, ordering, credits, and mobile layout are approved.
- [ ] External links and hosted media are reachable without editor access.
- [ ] Page preview, live page, social metadata, and search output are verified.
