import os
import django
import random
from faker import Faker
from datetime import datetime, timedelta
from django.utils import timezone

# Configurar entorno Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos.settings')
django.setup()

from posApp.models import CashRegister, User

fake = Faker()
current_year = datetime.now().year
usuarios = list(User.objects.all())

if not usuarios:
    print("❌ No hay usuarios en la base de datos.")
    exit()

for mes in range(1, 13):  # Enero (1) a Diciembre (12)
    for _ in range(30):  # 30 cajas por mes
        usuario = random.choice(usuarios)

        # Fecha de apertura aleatoria dentro del mes
        dia_apertura = random.randint(1, 28)  # Para evitar errores con meses cortos
        opening_date = datetime(current_year, mes, dia_apertura, random.randint(8, 12), random.randint(0, 59))

        # Fecha de cierre unas horas o días después (opcionalmente nula para representar "caja abierta")
        if random.choice([True, False]):
            close_date = opening_date + timedelta(hours=random.randint(4, 12))
        else:
            close_date = None  # Caja aún abierta

        CashRegister.objects.create(
            opening_date=opening_date,
            close_date=close_date,
            user=usuario
        )

    print(f"✅ Se crearon 30 cajas para el mes {mes:02d}/{current_year}")

print("🎉 ¡Listo! Todas las cajas fueron creadas.")
