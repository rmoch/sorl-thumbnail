# -*- coding: utf-8 -*-
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url  # keep django <1.4 compatibility
from django.conf import settings
from django.views.generic import TemplateView


class TestTemplateView(TemplateView):
    def get_template_names(self):
        return self.request.META['PATH_INFO'].split('/')[1]


urlpatterns = patterns('',
    (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT,
        'show_indexes': True}
    ),
    (r'^(.*\.html)$',  TestTemplateView.as_view()),
)

