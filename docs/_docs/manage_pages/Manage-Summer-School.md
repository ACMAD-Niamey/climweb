# Manage the ACMAD Summer School

The Summer School module contains one programme index, one page per edition, and an optional application form below each
edition. It can also be served as the root of a dedicated Wagtail Site.

## Page hierarchy

```text
Main ACMAD Home Page
└── Summer School Index Page (maximum one)
    └── Summer School Page (one per edition)
        └── Summer School Application Page (maximum one per edition)
```

## Programme index

Edit the index to maintain its hero heading, subtitle, description, badges, background image, bottom banner, and number
of editions per page. The listing separates the featured edition from other editions and supports current/archive,
year, search, and pagination behavior.

Check that editions have an `edition_start_date`; it controls ordering and archive behavior.

## Create an edition

Under the index, add a **Summer School Page** and complete:

- hero and programme tagline;
- internal or external calls to action (an external URL overrides the internal page choice);
- dates, start date, location, format, language, certificate, and contact;
- index-card icon, status label, and featured image;
- background, eligibility, prerequisites, structure, trainers, schedule, and cohorts;
- concept note, additional materials, partners, and FAQ;
- daily activities and reviews when the candidate release includes them;
- SEO metadata and settings.

Only one edition should normally be marked **Featured**. Use **Is hidden** for deliberate listing suppression, not as a
substitute for unpublishing sensitive or incorrect content. Review **Visible on homepage** and the homepage carousel
separately.

## Daily activities and reviews

The later Summer School feature line adds one activity entry per day with summary, photos, uploaded videos, and hosted
video links. It also supports reviews collected from social platforms and feedback forms.

Before publication:

- obtain permission for identifiable participants and testimonials;
- provide meaningful image titles/alt text;
- verify hosted-video privacy and availability;
- use approved quotations without altering meaning;
- avoid publishing registration data or private feedback;
- confirm the release contains the corresponding migrations and templates.

## Application form lifecycle

Add one **Summer School Application Page** below the edition. Configure introduction, illustration, deadline, journey,
form fields, validation field, thank-you text, email routing, submission ratings, and reviewer notifications.

Use a stable, unique validation field—normally the clean name for email—to prevent unintended duplicate submissions.
Test the actual form field name after editing fields.

Before opening applications:

1. Publish the edition and form.
2. Set the deadline and confirm server timezone behavior.
3. Submit a test using non-sensitive data.
4. Confirm acknowledgement and internal notification delivery.
5. Verify duplicate prevention, CAPTCHA, exports, reviewer access, and closing behavior.
6. Delete or clearly label test submissions according to policy.

Closing applications requires both an editorial message and the correct application setting/deadline. Verify the public
button and direct form URL.

## Homepage and dedicated hostname

The homepage can show Summer School through latest-update content and the configurable carousel. Review the index's
featured edition and the homepage visibility/order together.

For dedicated-host setup, follow the Subdomain Deployment and TLS guides. Verify that using the index as a Wagtail Site
root still produces correct metadata, links, static assets, forms, and navigation.

## Privacy and retention

Application submissions may contain personal data. Document:

- purpose and lawful/approved use;
- who can view, rate, export, and delete submissions;
- retention and deletion date;
- how exported files are protected;
- participant consent for public activity media and reviews.

Do not attach application exports to tickets or the Git repository.

## Acceptance checklist

- [ ] Index and edition hierarchy is correct.
- [ ] Featured/current/archive ordering is correct.
- [ ] Calls to action and application state match the programme decision.
- [ ] Application submission, notifications, duplicate check, deadline, and export are tested.
- [ ] Concept note and additional downloads are current.
- [ ] Trainers, schedule, partners, activities, reviews, photos, and videos are approved.
- [ ] Homepage and dedicated-host presentation are validated on mobile and desktop.
- [ ] Submission retention, reviewer access, and responsible owner are recorded.
