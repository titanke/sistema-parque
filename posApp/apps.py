from django.apps import AppConfig
from django.db.models.signals import post_delete

class posAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'posApp'
    

    def ready(self):
        # Importamos los módulos necesarios DENTRO de ready()
        from . import signals
        from .models import Sales # Importa aquí tu modelo

        # Conectamos la señal manualmente
        post_delete.connect(
            signals.log_delete_event,
            sender=Sales,
            dispatch_uid="log_delete_event_for_sales" # Un ID único para la señal
        )