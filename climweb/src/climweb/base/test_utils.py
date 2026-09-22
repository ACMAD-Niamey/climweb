def test_page_meta_tags(test_case, page, meta_tags, request=None, check_image=True, check_description=True):
    from climweb.base.models import OrganisationSetting

    # check title — the browser-tab <title> is the page meta title with the
    # organisation name (or, failing that, the Wagtail site name) appended;
    # see templates/wagtailmetadata/parts/tags.html
    test_case.assertIsNotNone(meta_tags["title"])
    site = page.get_site()
    brand = (OrganisationSetting.for_site(site).name or site.site_name) if site else None
    expected_title = page.get_meta_title()
    if brand:
        expected_title = f"{expected_title} — {brand}"
    test_case.assertEqual(meta_tags["title"], expected_title)
    
    if check_description:
        # check meta_description
        test_case.assertIsNotNone(meta_tags["meta_description"])
        test_case.assertIsNotNone(meta_tags["meta_description"])
    
    # check meta url
    test_case.assertIsNotNone(meta_tags["meta_url"])
    test_case.assertEqual(meta_tags["meta_url"], page.full_url)
    
    if check_image:
        # check meta image
        test_case.assertIsNotNone(meta_tags["meta_image"])
        test_case.assertEqual(meta_tags["meta_image"], page.get_meta_image_url(request))
    
    # check site name
    test_case.assertIsNotNone(meta_tags["meta_name"])
    test_case.assertEqual(meta_tags["meta_name"], page.get_site().site_name)
