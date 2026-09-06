"""Hạ tầng chung — không thuộc domain nào trong 6 app."""

from django.views.generic import TemplateView


class IndexView(TemplateView):
    """Trả index.html cho mọi route non-API; Vue Router xử lý phía client."""

    template_name = "index.html"
