# 🌤️🌐 ClimWeb 

<a href="https://digitalpublicgoods.net/r/climweb"><img src="https://github.com/DPGAlliance/dpg-resources/blob/main/docs/assets/dpg-badge/dpg-badge.png?raw=true" width="100" alt="Digital Public Goods Badge"></a>

Wagtail based Open Source Content Management System for National Meteorological and Hydrological Services in Africa.

A website template co-developed with NMHSs in Africa to support their digital transformation. Aims to adopt best
practices in web design and development, data visualization and hydro meteorological and climate communications to
ensure that NMHSs have a modern, responsive, and user-friendly website.


ClimWeb is open-source software, recognised as a Digital Public Good by the Digital Public Goods Alliance. It strengthens the delivery of climate services, contributing to the Sustainable Development Goals, including SDG 13 (Climate Action). 

## ACMAD Fork

This is [ACMAD](https://www.acmad.org/)'s fork of ClimWeb, deployed at [new.acmad.org](https://new.acmad.org). For
the base CMS platform, its full feature set, and general documentation, see the upstream project at
[wmo-raf/nmhs-cms](https://github.com/wmo-raf/nmhs-cms) (reference Docker deployment:
[wmo-raf/climweb-docker](https://github.com/wmo-raf/climweb-docker)).

### What's implemented in this fork

- **Summer School module** - dedicated page types for the programme index, yearly editions, and applications, with
  eligibility, application journey, CV upload, and partners sections, plus the featured edition surfaced on the
  main homepage.
- **Summer School on its own subdomain** - `summerschool.acmad.org` serves the module directly at `/`, sharing the
  same application and database as the main site via Wagtail multi-site. See
  [docs/_docs/technical/subdomain-deployment.md](docs/_docs/technical/subdomain-deployment.md) for how it's wired
  up and the gotchas involved.
- **Submission review & rating system** - staff can rate and comment on form submissions, with bulk email and a
  weekly submission-count digest, for any form page sitewide.
- **Max-length option for multi-line form fields** - optional character limit, enforced both server-side and via
  the browser's native `maxlength`.

See [docs/_docs/technical/deployment.md](docs/_docs/technical/deployment.md) for how this fork's instance is
actually built and deployed (CI/CD pipeline, production host setup).

## Live Instances

This fork only tracks ACMAD's own deployment ([new.acmad.org](https://new.acmad.org) and
[summerschool.acmad.org](https://summerschool.acmad.org)) - it doesn't track adoption elsewhere, so a copied list
here would just go stale. For the current, maintained list of NMHSs and other organizations running ClimWeb across
Africa and beyond, see the
[Live Instances section of the upstream README](https://github.com/wmo-raf/nmhs-cms#live-instances).

## 🌟 Core Features

- 🙂 User friendly website Content Management System
    - Modern look and design, mobile friendly.
    - Adopts best practices and designs benchmarked for weather and climate information dissemination for NMHSs in
      Africa.
    - Easy to use and customise without technical skills.
    - Decentralised content management. Different staff can be assigned and manage different sections of the website.
    - Defined content publishing workflows. Editors and moderators can be defined for every section of the website.
    - Embedding Multimedia Content - Youtube etc.

- ⚠️ Cap Alerts Publishing
    - Modern Cap Warnings Composer with simple user friendly and mobile friendly CAP alert creation and management.
    - Moderated Publishing Workflow from CAP composer to approver, including commenting and email notification support.
    - Conforms to CAP Version 1.2 Standards.
    - Search Engine Optimisation support to increase visibility and attract targeted traffic to an alert.
    - Support for Approval Workflow from composer to approver, including commenting and email notification support.
    - Interoperable XML API of Alert List and Detail for integration with CAP Aggregators
    - Live CAP creation and editing preview.
    - Draw/Select predefined Alert areas.
    - Alert to Alert/Alerts Reference Linkage.

- 📆 Events registrations and Integration with Online Meeting Platforms (Zoom)
    - Create event registration forms hosted on the website.
    - Automatically send invitation emails to users as they register to events from the website.
    - Keep record of all your registrants for internal analysis.
    - Allow users registering to events to also subscribe to your products.
- 🌍 Interactive Georeferenced data visualisation
    - Upload and visualise own gridded data (forecasts, advisories, climate data products) on a map.
    - Upload and visualise vector data (Point, areas) on a map.
    - Visualise own CAP alerts.
    - Visualise thematic/sectorial data products interactively.
    - Integrate external data sources ( from Regional Centers, Global Producing Centers, Satellite, Google Earth Engine
      etc).
    - Provide a platform to support impact based forecasts, analysis and advisories.

- 📧 Email Marketing integration and user analytics
    - Sign Up forms for users to subscribe to NMHSs products (using Mautic or Mailchimp).
    - Analyse your email marketing users data.
- 📋 Survey creation and results analysis
    - Create custom surveys hosted on own website.
    - Analyse results on interactive dashboards.
- 📈 User analytics
    - User base breakdown (eg. by sectors, gender, geographic area, etc, from user database - email marketing software).
    - User satisfaction (from surveys) data and trends .
    - Website traffic analytics (eg. google analytics) .
- 😎 And many more others feature added iteratively, as per the needs of the NMHSs.

## 💻 Technical & Development

For technical and local development details, please refer to
the [Technical Guide](https://climweb.readthedocs.io/en/latest/_docs/technical/index.html) section of the documentation.

## 📕 User Guide

Read more from the user guide - [https://climweb.readthedocs.io/](https://climweb.readthedocs.io/)

---

## 🛠️ Production deployment with Docker Installation Guide

For installation instructions with docker, please visit https://github.com/wmo-raf/climweb-docker
