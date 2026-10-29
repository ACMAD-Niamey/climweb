from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page

from climweb.base import blocks
from climweb.base.models import AbstractBannerWithIntroPage
from climweb.pages.videos.models import YoutubePlaylist


class MediaIndexPage(AbstractBannerWithIntroPage):
    template = 'mediacenter_index.html'
    parent_page_types = ['home.HomePage']
    subpage_types = []
    max_count = 1

    feature_block_items = StreamField(
        [
            ('feature_item', blocks.MediaFeatureBlock()),
        ],
        null=True, blank=True, verbose_name=_("Items"), use_json_field=True)

    youtube_playlist = models.ForeignKey(
        YoutubePlaylist,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Youtube playlist")
    )

    introduction_video_url = models.URLField(
        blank=True,
        verbose_name=_("Introduction video URL"),
        help_text=_(
            "Optional YouTube or Vimeo URL. When provided, the video replaces "
            "the introduction image."
        ),
    )
    more_media_title = models.CharField(
        max_length=120,
        default=_("More Media"),
        verbose_name=_("More media section title"),
    )

    content_panels = Page.content_panels + [
        *AbstractBannerWithIntroPage.content_panels,
        FieldPanel('introduction_video_url'),
        FieldPanel('more_media_title'),
        FieldPanel('feature_block_items'),
        FieldPanel('youtube_playlist'),
    ]

    class Meta:
        verbose_name = _("Media Page")

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        if self.youtube_playlist:
            context['youtube_playlist_url'] = self.youtube_playlist.get_playlist_items_api_url(request)

        return context
