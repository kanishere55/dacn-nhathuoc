from importlib import import_module

from django.apps import AppConfig


class ChungConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ung_dung.chung"
    verbose_name = "Phần dùng chung"

    def ready(self):
        import_module("ung_dung.chung.kiem_tra_luu_tru")
