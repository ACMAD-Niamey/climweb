import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'climweb.config.settings.base')
django.setup()

from climweb.pages.events.models import EventPage
from wagtail.admin.rich_text.converters.html_to_contentstate import HtmlToContentStateHandler

for page in EventPage.objects.all():
    if not page.description: continue
    handler = HtmlToContentStateHandler(features=["bold", "ul", "ol", "link", "superscript", "subscript", "h2", "h3", "h4"])
    try:
        handler.feed(page.description)
        handler.close()
    except AssertionError as e:
        if "expected" in str(e) or "Unmatched" in str(e):
            print(f"Error on Page ID {page.id}: {e}")
            print("HTML:")
            print(repr(page.description))
            break
