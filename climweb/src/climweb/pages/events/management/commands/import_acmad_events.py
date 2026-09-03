import urllib.request
import json
import ssl
import html
import re
from datetime import datetime, timezone
import pytz

from django.core.management.base import BaseCommand
from climweb.pages.events.models import EventPage, EventIndexPage, EventType

class Command(BaseCommand):
    help = 'Imports missing events from acmad.org'

    def handle(self, *args, **options):
        self.stdout.write("Fetching events from acmad.org...")
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        def fetch_json(url):
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
                    return json.loads(response.read().decode())
            except Exception as e:
                self.stderr.write(f"Error fetching {url}: {e}")
                return []

        events_data = []

        # 1. Fetch Posts
        posts = fetch_json('https://acmad.org/wp-json/wp/v2/posts?per_page=100')
        for p in posts:
            cats = p.get('categories', [])
            if 1 in cats or 13 in cats:
                events_data.append(p)

        # 2. Fetch Pages
        pages = []
        for page_num in range(1, 4):
            pages.extend(fetch_json(f'https://acmad.org/wp-json/wp/v2/pages?per_page=100&page={page_num}'))

        event_parent_ids = [p['id'] for p in pages if 'event' in p.get('slug', '').lower() and len(p.get('slug', '')) <= 7]

        keywords = ['forum', 'workshop', 'meeting', 'training', 'cop', 'accof', 'presac', 'presass', 'presagg', 'event']
        for p in pages:
            title = html.unescape(p.get('title', {}).get('rendered', '')).strip()
            slug = p.get('slug', '').lower()
            
            is_event = False
            if p.get('parent') in event_parent_ids:
                is_event = True
            elif any(kw in slug for kw in keywords) or any(kw in title.lower() for kw in keywords):
                is_event = True
                
            if is_event:
                events_data.append(p)

        # Remove duplicates
        unique_events = {}
        for ev in events_data:
            t = html.unescape(ev.get('title', {}).get('rendered', '')).strip()
            if t not in unique_events:
                unique_events[t] = ev
        
        events_data = list(unique_events.values())
        self.stdout.write(f"Found {len(events_data)} potential events on acmad.org.")

        # Get EventIndexPage
        index_page = EventIndexPage.objects.first()
        if not index_page:
            self.stderr.write("Error: EventIndexPage not found. Create one in Wagtail admin first.")
            return

        default_event_type, _ = EventType.objects.get_or_create(event_type="Other")
        imported_count = 0
        skipped_count = 0

        for p in events_data:
            title = html.unescape(p.get('title', {}).get('rendered', '')).strip()
            
            # Check if exists
            if EventPage.objects.filter(title=title).exists():
                skipped_count += 1
                continue

            # Extract data
            content = p.get('content', {}).get('rendered', '')
            date_str = p.get('date_gmt') or p.get('date')
            
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=pytz.UTC)
            except:
                dt = datetime.now(pytz.UTC)

            # Create EventPage
            page = EventPage(
                title=title,
                date_from=dt,
                location='Niamey, Niger',  # Default fallback
                description=content,
                event_type=default_event_type,
                registration_open=False, # default to False for old events
            )
            
            try:
                index_page.add_child(instance=page)
                page.save_revision().publish()
                self.stdout.write(self.style.SUCCESS(f"Imported: {title}"))
                imported_count += 1
            except Exception as e:
                self.stderr.write(f"Failed to import '{title}': {e}")

        self.stdout.write(self.style.SUCCESS(f"\nDone! Imported {imported_count} new events. Skipped {skipped_count} existing ones."))
