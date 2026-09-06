"""Hạ tầng chung — không thuộc domain nào trong 6 app."""

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IndexView(TemplateView):
    """Trả index.html cho mọi route non-API; Vue Router xử lý phía client.

    `ensure_csrf_cookie`: SPA nạp trang trước khi gọi API, nên cookie `csrftoken`
    phải có sẵn từ lần tải trang đầu — kể cả khi người dùng chưa đăng nhập.
    """

    template_name = "index.html"
