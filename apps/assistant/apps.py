from django.apps import AppConfig


class AssistantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.assistant"
    verbose_name = "AI Assistant"

    def ready(self):
        # Register all post_save signals for automatic re-indexing
        from apps.assistant.signals import register_signals
        register_signals()
