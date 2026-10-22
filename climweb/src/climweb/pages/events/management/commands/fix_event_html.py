from django.core.management.base import BaseCommand
from bs4 import BeautifulSoup
from climweb.pages.events.models import EventPage

class Command(BaseCommand):
    help = 'Fixes malformed HTML in EventPage descriptions (e.g. Unmatched tags: expected br, got td)'

    def handle(self, *args, **options):
        events = EventPage.objects.all()
        updated_count = 0

        self.stdout.write(f"Checking {events.count()} EventPages for malformed HTML...")

        for page in events:
            if not page.description:
                continue

            content = page.description
            soup = BeautifulSoup(content, 'html.parser')
            modified = False

            tags_to_unwrap = ['table', 'tbody', 'thead', 'tfoot', 'tr', 'td', 'th', 'div', 'span', 'font', 'section', 'article']
            for tag_name in tags_to_unwrap:
                for tag in soup.find_all(tag_name):
                    tag.unwrap()
                    modified = True
            
            if modified:
                page.description = str(soup)
                # Save the page
                is_live = page.live
                if is_live:
                    page.save_revision().publish()
                else:
                    page.save_revision()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"Fixed HTML for Event: {page.title} (ID: {page.id})"))

        self.stdout.write(self.style.SUCCESS(f"Done! Fixed {updated_count} events."))
