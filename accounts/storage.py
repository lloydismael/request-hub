from __future__ import annotations

from django.apps import apps
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.urls import reverse
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseMediaStorage(Storage):
    """Store uploaded files inside the database via the StoredFile model."""

    def _file_model(self):
        return apps.get_model("accounts", "StoredFile")

    def _open(self, name, mode="rb"):
        model = self._file_model()
        try:
            stored_file = model.objects.get(name=name)
        except model.DoesNotExist as exc:
            raise FileNotFoundError(name) from exc
        return ContentFile(stored_file.data, name=stored_file.original_name or name.split("/")[-1])

    def _save(self, name, content):
        model = self._file_model()
        data = content.read()
        content.seek(0)
        content_type = getattr(content, "content_type", "") or ""
        original_name = getattr(content, "name", "") or ""
        model.objects.update_or_create(
            name=name,
            defaults={
                "data": data,
                "content_type": content_type,
                "original_name": original_name,
                "size": len(data),
            },
        )
        return name

    def delete(self, name):
        model = self._file_model()
        model.objects.filter(name=name).delete()

    def exists(self, name):
        model = self._file_model()
        return model.objects.filter(name=name).exists()

    def url(self, name):
        return reverse("accounts:media", kwargs={"name": name})

    def size(self, name):
        model = self._file_model()
        try:
            stored_file = model.objects.only("size").get(name=name)
        except model.DoesNotExist as exc:
            raise FileNotFoundError(name) from exc
        return stored_file.size
