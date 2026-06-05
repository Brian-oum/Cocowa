from django.apps import AppConfig


class SystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'System'
    def ready(self):
        import System.signals