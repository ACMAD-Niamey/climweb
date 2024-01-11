from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from googleapiclient.discovery import build
from wagtail.admin.panels import (FieldPanel)
from wagtail.api.v2.utils import get_full_url
from wagtail.models import Site
from wagtail.snippets.models import register_snippet

from base.models import IntegrationSettings

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
youtube_service = None


@register_snippet
class YoutubePlaylist(models.Model):
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    playlist_id = models.CharField(max_length=100,
                                   help_text=_("This is the playlist ID as obtained from Youtube. "
                                               "If the playlist is not created on Youtube, please create it first"),
                                   verbose_name=_("Playlist ID"))

    def set_api(self):
        try:
            current_site = Site.objects.get(is_default_site=True)

            # Get the SiteSettings for the current site
            settings = IntegrationSettings.for_site(current_site)
            api_key = settings.youtube_api
            YOUTUBE_API_KEY = api_key

            # creating Youtube Resource Object
            self.youtube_service = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                                         developerKey=YOUTUBE_API_KEY)

            return self.youtube_service

        except Exception as e:
            print("Error: ", e)
            pass

    def __str__(self):
        return self.title

    def get_playlist_items_api_url(self, request=None):
        api_url = reverse("youtube_playlist_items", args=[self.pk])
        api_url = get_full_url(request, api_url)
        return api_url

    @property
    def videos_count(self):
        # Get the current site
        youtube_service = self.set_api()

        if youtube_service:
            info = None
            try:
                videos = youtube_service.playlistItems().list(part="snippet",
                                                              playlistId=self.playlist_id).execute()

                if "pageInfo" in videos:
                    info = videos['pageInfo']['totalResults']
            except:
                pass
            return info
        return None

    def playlist_items(self, limit=None):
        youtube_service = self.set_api()

        if youtube_service:
            info = None
            try:
                videos = youtube_service.playlistItems().list(part="snippet,contentDetails",
                                                              playlistId=self.playlist_id,
                                                              maxResults=limit).execute()

                if "items" in videos:
                    info = videos['items']
            except:
                pass

            if info:
                # sort by video position in playlist
                info.sort(key=lambda info_item: info_item['snippet']['position'], reverse=True)
            return info
        return None

    panels = [
        FieldPanel('title'),
        FieldPanel('playlist_id'),
    ]
