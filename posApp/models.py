from datetime import datetime
from unicodedata import category
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

# Create your models here.


class Category(models.Model):
    name = models.TextField()
    description = models.TextField()
    status = models.IntegerField(default=1) 
    date_added = models.DateTimeField(default=timezone.now) 
    date_updated = models.DateTimeField(auto_now=True) 

    def __str__(self):
        return self.name

class Products(models.Model):
    code = models.CharField(max_length=100)
    category_id = models.ForeignKey(Category, on_delete=models.RESTRICT)
    name = models.TextField()
    description = models.TextField()
    price = models.FloatField(default=0)
    p_mayor = models.FloatField(default=0)
    stock = models.IntegerField(default=0)
    status = models.IntegerField(default=1) 
    date_added = models.DateTimeField(default=timezone.now) 
    date_updated = models.DateTimeField(auto_now=True)
    image = models.URLField(max_length=200, blank=True, null=True)  

    #image = models.ImageField(upload_to='products/', null=True, blank=True)  
    """
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)  
        self.image.delete(save=False)  
      
    """
    def __str__(self):
        return self.code + " - " + self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/', null=True, blank=True)  

    
class PaymentType(models.Model):
    name = models.TextField()
    status = models.IntegerField(default=1) 
    date_added = models.DateTimeField(default=timezone.now) 
    date_updated = models.DateTimeField(auto_now=True) 

    def __str__(self):
        return self.name
    
    
class CashRegister(models.Model):
    opening_amount = models.FloatField(default=0)
    opening_date = models.DateTimeField(default=timezone.now)
    close_date = models.DateTimeField(null=True, blank=True)
    sales = models.ManyToManyField('Sales', through='CashRegisterSales')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Caja {self.id}"

class Expense(models.Model):
    description = models.CharField(max_length=255)
    amount = models.FloatField()
    expense_date = models.DateTimeField(default=timezone.now)
    cash_register = models.ForeignKey(CashRegister, on_delete=models.CASCADE, related_name='expenses', default=1) 

    def __str__(self):
        return self.description
    
    
class Sales(models.Model):
    code = models.CharField(max_length=100)
    sub_total = models.FloatField(default=0)
    grand_total = models.FloatField(default=0)
    descuento = models.FloatField(default=0)
    tax_amount = models.FloatField(default=0)
    tax = models.FloatField(default=0)
    payment_type_id = models.ForeignKey('PaymentType', on_delete=models.RESTRICT)
    tendered_amount = models.FloatField(default=0)
    amount_change = models.FloatField(default=0)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code

class CashRegisterSales(models.Model):
    cash_register = models.ForeignKey(CashRegister, on_delete=models.CASCADE)
    sale = models.ForeignKey(Sales, on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cash_register', 'sale')

#Caracteristicas
class Size(models.Model):
    name = models.CharField(max_length=50, unique=True)  # Por ejemplo: "S", "M", "L", etc.
    status = models.IntegerField(default=1) 
    date_added = models.DateTimeField(default=timezone.now) 
    date_updated = models.DateTimeField(auto_now=True) 
    
    def __str__(self):
        return self.name

class Color(models.Model):
    name = models.CharField(max_length=50, unique=True)  # Por ejemplo: "Rojo", "Azul", etc.
    status = models.IntegerField(default=1) 
    date_added = models.DateTimeField(default=timezone.now) 
    date_updated = models.DateTimeField(auto_now=True) 
    
    def __str__(self):
        return self.name
    

class ProductFeature(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name="features")
    size = models.ForeignKey(Size, on_delete=models.RESTRICT)  # Relación con la tabla de tallas
    color = models.ForeignKey(Color, on_delete=models.RESTRICT)  # Relación con la tabla de colores
    stock = models.IntegerField(default=0)  # Stock de esta combinación específica

    class Meta:
        unique_together = ('product', 'size', 'color')  # Evita duplicados de combinaciones

    def __str__(self):
        return f"{self.product.name} - Talla: {self.size.name}, Color: {self.color.name}"

    def update_stock(self, quantity):
        """
        Actualiza el stock de esta combinación específica y valida que no exceda el stock general.
        """
        if quantity < 0 and abs(quantity) > self.stock:
            raise ValueError("No puedes reducir más stock del que hay disponible para esta combinación.")
        if quantity > 0 and (self.product.stock - self.product_total_features_stock() < quantity):
            raise ValueError("No puedes exceder el stock general del producto.")
        self.stock += quantity
        self.save()

    def product_total_features_stock(self):
        """
        Calcula el stock total de todas las características del producto.
        """
        return sum(feature.stock for feature in self.product.features.all())


class salesItems(models.Model):
    sale_id = models.ForeignKey(Sales,on_delete=models.CASCADE)
    product_id = models.ForeignKey(Products,on_delete=models.RESTRICT)
    feature_id = models.ForeignKey(ProductFeature, on_delete=models.CASCADE, null=True, blank=True)  
    price = models.FloatField(default=0)
    qty = models.FloatField(default=0)
    total = models.FloatField(default=0)
    
    
