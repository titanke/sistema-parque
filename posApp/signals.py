# posApp/signals.py

from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from .models import Sales 


def log_delete_event(sender, instance, **kwargs):
    deleted_data = model_to_dict(instance)
    
    keys_to_exclude = ['date_added', 'date_updated']
    
    filtered_data = {
        key: value for key, value in deleted_data.items() 
        if key not in keys_to_exclude
    }

    changes_dict = {key: [value, None] for key, value in filtered_data.items()}

    LogEntry.objects.create(
        content_type=ContentType.objects.get_for_model(Sales),
        object_pk=instance.pk,
        object_repr=f"Se eliminó el objeto '{instance}'.",
        action=LogEntry.Action.DELETE,
        changes=changes_dict # <-- ¡Pasa el diccionario, no la cadena JSON!
    )
    
