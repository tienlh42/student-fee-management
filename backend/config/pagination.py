"""Phân trang chung — cho phép client tự chọn số dòng mỗi trang.

`PageNumberPagination` mặc định bỏ qua `?page_size=`, nên DataTable đổi
"số dòng mỗi trang" sẽ không có tác dụng nếu không mở query param này.
"""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
