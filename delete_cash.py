import os
import django

# Configurar entorno Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos.settings')
django.setup()

from posApp.models import CashRegisterSales, CashRegister

# Borrar todos los items primero (porque dependen de Sales)
CashRegisterSales.objects.all().delete()

# Luego borrar las ventas
CashRegister.objects.all().delete()

print("✅ Registros eliminados.")
