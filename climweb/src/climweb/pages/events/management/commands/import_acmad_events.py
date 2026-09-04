import urllib.request
import json
import ssl
import html
import re
import os
import tempfile
from datetime import datetime, timezone
import pytz
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.core.files import File
from wagtail.images.models import Image
from bs4 import BeautifulSoup
from climweb.base.models import CustomDocumentModel
from climweb.pages.events.models import EventPage, EventIndexPage, EventType

class Command(BaseCommand):
    help = 'Imports missing events from acmad.org including documents and images'

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
                
        def download_file(url, is_image=False):
            if not url or url.startswith('data:'):
                return None
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
                    filename = os.path.basename(urlparse(url).path)
                    if not filename:
                        filename = "downloaded_file"
                    
                    temp = tempfile.NamedTemporaryFile(delete=False)
                    temp.write(response.read())
                    temp.flush()
                    temp.close()
                    
                    if is_image:
                        obj = Image(title=filename)
                        with open(temp.name, 'rb') as f:
                            obj.file.save(filename, File(f), save=True)
                        os.unlink(temp.name)
                        return obj
                    else:
                        obj = CustomDocumentModel(title=filename)
                        with open(temp.name, 'rb') as f:
                            obj.file.save(filename, File(f), save=True)
                        os.unlink(temp.name)
                        return obj
            except Exception as e:
                self.stderr.write(f"Error downloading {url}: {e}")
                return None

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
        updated_count = 0

        for p in events_data:
            title = html.unescape(p.get('title', {}).get('rendered', '')).strip()
            
            content = p.get('content', {}).get('rendered', '')
            if not content:
                content = "<p>Event details not provided.</p>"
            else:
                # Sanitize HTML to prevent Draftail errors (e.g. "Unmatched tags: expected br, got td")
                soup = BeautifulSoup(content, 'html.parser')
                for br in soup.find_all('br'):
                    if br.parent and br.parent.name in ['table', 'tbody', 'thead', 'tfoot', 'tr']:
                        br.decompose()
                content = str(soup)
            
            # Process embedded images
            img_pattern = re.compile(r'<img[^>]*src="([^"]+)"[^>]*>')
            for match in img_pattern.finditer(content):
                img_url = match.group(1)
                image_obj = download_file(img_url, is_image=True)
                if image_obj:
                    embed_tag = f'<embed embedtype="image" id="{image_obj.id}" format="fullwidth" alt="{image_obj.title}"/>'
                    content = content.replace(match.group(0), embed_tag)
                    self.stdout.write(f"  Downloaded embedded image: {img_url}")
            
            # Process documents
            doc_pattern = re.compile(r'<a[^>]*href="([^"]+\.(?:pdf|doc|docx|ppt|pptx|xls|xlsx))"[^>]*>(.*?)</a>', re.IGNORECASE)
            agenda_doc = None
            for match in doc_pattern.finditer(content):
                doc_url = match.group(1)
                link_text = match.group(2)
                doc_obj = download_file(doc_url, is_image=False)
                if doc_obj:
                    if not agenda_doc:
                        agenda_doc = doc_obj
                    link_tag = f'<a linktype="document" id="{doc_obj.id}">{link_text}</a>'
                    content = content.replace(match.group(0), link_tag)
                    self.stdout.write(f"  Downloaded document: {doc_url}")

            # Featured Image
            featured_media_id = p.get('featured_media')
            featured_image_obj = None
            if featured_media_id:
                media_data = fetch_json(f'https://acmad.org/wp-json/wp/v2/media/{featured_media_id}')
                if isinstance(media_data, dict) and 'source_url' in media_data:
                    featured_image_obj = download_file(media_data['source_url'], is_image=True)
                    self.stdout.write(f"  Downloaded featured image: {media_data['source_url']}")

            date_str = p.get('date_gmt') or p.get('date')
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=pytz.UTC)
            except:
                dt = datetime.now(pytz.UTC)

            existing_page = EventPage.objects.filter(title=title).first()
            if existing_page:
                existing_page.description = content
                if featured_image_obj:
                    existing_page.image = featured_image_obj
                if agenda_doc:
                    existing_page.agenda_document = agenda_doc
                existing_page.save_revision()
                if existing_page.live:
                    existing_page.unpublish()
                self.stdout.write(self.style.SUCCESS(f"Updated existing: {title}"))
                updated_count += 1
            else:
                page = EventPage(
                    title=title,
                    date_from=dt,
                    location='Niamey, Niger',
                    description=content,
                    event_type=default_event_type,
                    registration_open=False,
                    image=featured_image_obj,
                    agenda_document=agenda_doc,
                    live=False
                )
                try:
                    index_page.add_child(instance=page)
                    page.save_revision()
                    if page.live:
                        page.unpublish()
                    self.stdout.write(self.style.SUCCESS(f"Imported new: {title}"))
                    imported_count += 1
                except Exception as e:
                    self.stderr.write(f"Failed to import '{title}': {e}")

        self.stdout.write(self.style.SUCCESS(f"\nDone! Imported {imported_count} new events. Updated {updated_count} existing events with images/documents."))
