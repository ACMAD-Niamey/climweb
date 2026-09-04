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

            # Find all <br> and <br/> tags
            for br in soup.find_all('br'):
                # Draft.js / html5lib crashes if a <br> is a direct child of a table, tbody, thead, tfoot, or tr.
                # It expects them only inside <td> or <th>.
                if br.parent and br.parent.name in ['table', 'tbody', 'thead', 'tfoot', 'tr']:
                    br.decompose()
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
