"""Mixin cho ViewSet của model dùng `core.models.UserTrackingModel`.

View là nơi duy nhất biết `request.user` — set created_by_user/updated_by_user
ở đây, không phải trong service (xem docstring UserTrackingModel).
"""


class UserTrackingViewSetMixin:
    """Gắn vào ViewSet cùng với `ScopedModelViewSet` (hoặc tương đương):

        class FeePackageViewSet(UserTrackingViewSetMixin, ScopedModelViewSet):
            ...

    Model phải kế thừa `UserTrackingModel` và serializer phải khai
    `created_by_user`/`updated_by_user` là `read_only=True` — client không
    được tự xưng danh.
    """

    def perform_create(self, serializer):
        serializer.save(
            created_by_user=self.request.user, updated_by_user=self.request.user
        )

    def perform_update(self, serializer):
        serializer.save(updated_by_user=self.request.user)
