# Proposed ACMAD Product Taxonomy

Generated: 2026-08-05T10:08:16+00:00

## Audit summary

- Inventory records: 118
- Product/product-link records: 108
- Unique linked endpoints checked: 72
- Endpoints responding below HTTP 400: 57
- Endpoints broken, blocked, or timing out: 15

This is a review proposal, not an import log. Similar legacy entries are intentionally consolidated into stable product families.

## Proposed product families

| Priority | Target ProductPage | Discovered records | Recommended handling |
|---|---|---:|---|
| P0 | Continental Drought | 2 | synchronize |
| P0 | Continental Multi-Hazard Outlook | 2 | synchronize |
| P0 | Dekadal Climate Bulletin | 3 | synchronize |
| P0 | Policy and Decision Briefs | 2 | synchronize |
| P1 | Atmospheric Analysis | 19 | synchronize |
| P1 | Daily Rainfall Monitoring | 20 | synchronize |
| P1 | Heat and Thermal Stress | 10 | synchronize |
| P1 | ITD and ITCZ Monitoring | 5 | synchronize |
| P1 | Numerical Weather Forecasts | 6 | synchronize |
| P1 | Thunderstorm and Nowcasting | 4 | synchronize |
| P2 | Agriculture Climate Services | 2 | copy_or_link_after_review |
| P2 | Climate Change and Projections | 2 | copy_or_link_after_review |
| P2 | Climate Monitoring | 3 | copy_or_link_after_review |
| P2 | Climate and Health | 3 | copy_or_link_after_review |
| P2 | Seasonal and Long-Range Forecasts | 25 | copy_or_link_after_review |

## Content-model mapping

- **ProductPage:** one stable product family, not one page per model variable or file.
- **ProductCategory:** a coherent format or subject grouping such as Bulletins, Observations, Forecast Maps, Technical Notes, or Data.
- **ProductItemType:** the specific layer or component, for example ECMWF Precipitation, ITD Position, or Flood Assessment.
- **ProductItemPage:** one issuance date containing all related images/documents for that issue.
- **External application:** keep live dashboards external and add an explicit external-product link rather than copying their HTML.

## Editorial decisions required

1. Confirm which operational systems are authoritative and expected to remain online.
2. Confirm whether ACCOF/PRESAC/SWIOCOF/GHACOF/SARCOF documents belong in Products or Publications.
3. Assign an ACMAD owner to each P0/P1 product family.
4. Confirm the historical cutoff date and whether all legacy files or only recent years should be copied.
5. Confirm copyright/redistribution permission for partner-hosted products.
6. Decide whether bilingual metadata is required during initial migration or as a second pass.

## Recommended pilot

Use **Continental Multi-Hazard Outlook** first. It already has a local ProductPage-equivalent, exposes a current archive, and exercises PDF, image, date, validity, archive, and scheduled-update behavior.

## Source catalogues

- [products_and_services](https://acmad.org/index.php/products-and-services/)
- [flagship_products](https://acmad.org/index.php/flagship-climate-services-products/)
- [data_center](https://acmad.org/index.php/data-center-2/)
- [bulletins](https://acmad.org/index.php/bulletins/)
- [climate_monitoring](https://acmad.org/index.php/acmad-climate-monitoring/)
