import os
import django
import random
from faker import Faker
from django.utils import timezone

# Configuración Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos.settings')
django.setup()

from posApp.models import (
    Sales, salesItems, Products, ProductFeature,
    CashRegister, CashRegisterSales, PaymentType, SalesPayment, User
)

fake = Faker()

productos = list(Products.objects.all())
cajas = list(CashRegister.objects.all())
tipos_pago = list(PaymentType.objects.all())

if not productos:
    print("❌ No hay productos.")
    exit()
if not cajas:
    print("❌ No hay cajas.")
    exit()
if not tipos_pago:
    print("❌ No hay tipos de pago.")
    exit()

for _ in range(100):
    subtotal = round(random.uniform(50, 500), 2)
    descuento = round(random.uniform(0, 20), 2)
    tax = 0.18
    tax_amount = round((subtotal - descuento) * tax, 2)
    grand_total = round(subtotal - descuento + tax_amount, 2)
    tendered = round(grand_total + random.uniform(0, 50), 2)
    change = round(tendered - grand_total, 2)
    fecha = fake.date_time_this_year(tzinfo=None)

    sale = Sales.objects.create(
        code=fake.uuid4(),
        sub_total=subtotal,
        grand_total=grand_total,
        descuento=descuento,
        tax_amount=tax_amount,
        tax=tax,
        tendered_amount=tendered,
        amount_change=change,
        date_added=fecha,
    )

    for _ in range(random.randint(1, 5)):
        product = random.choice(productos)
        feature = ProductFeature.objects.filter(product_id=product).order_by('?').first()
        qty = random.randint(1, 5)
        price = product.price
        total = round(price * qty, 2)

        salesItems.objects.create(
            sale_id=sale,
            product_id=product,
            feature_id=feature,
            price=price,
            qty=qty,
            total=total
        )

    # Relacionar con una caja aleatoria
    caja = random.choice(cajas)
    CashRegisterSales.objects.create(
        cash_register=caja,
        sale=sale
    )

    # Generar entre 1 y 2 métodos de pago por venta
    remaining = grand_total
    for i in range(random.randint(1, 2)):
        tipo = random.choice(tipos_pago)
        if i == 0:
            amount = round(random.uniform(1, remaining), 2)
        else:
            amount = round(remaining, 2)
        remaining -= amount

        SalesPayment.objects.create(
            sale=sale,
            payment_type=tipo,
            amount=amount
        )

print("✅ Datos de prueba generados correctamente.")
