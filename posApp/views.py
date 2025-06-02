from datetime import datetime, date
from calendar import monthrange
from urllib.parse import urlencode
from django.utils import timezone
from django.utils.dateparse import parse_date
from pickle import FALSE
from django.db.models import F, Sum
from django.utils.timezone import now
from collections import defaultdict
from django.contrib.auth.decorators import user_passes_test

from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse
from posApp.models import Category, Products, Sales, salesItems, PaymentType, Size, Color,ProductFeature, CashRegister, CashRegisterSales, Expense, SalesPayment
from django.db.models import Count, Sum
from django.contrib.auth.models import User

from django.db.models.deletion import ProtectedError
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.core.paginator import Paginator
from django.db.models import Q
import json, sys
from django.db import transaction


from django.core.files.storage import FileSystemStorage
from django.conf import settings

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import portrait
from reportlab.lib.utils import ImageReader

import os
# Login
def login_user(request):
    logout(request)
    resp = {"status":'failed','msg':''}
    username = ''
    password = ''
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                resp['status']='success'
            else:
                resp['msg'] = "Usuario o contraseña incorrecto"
        else:
            resp['msg'] = "Usuario o contraseña incorrecto"
    return HttpResponse(json.dumps(resp),content_type='application/json')

#Logout
def logoutuser(request):
    logout(request)
    return redirect('/')


@login_required
def home(request):
    now = timezone.now()
    current_year = now.year
    current_month = now.month
    current_day = now.day
    months = ['01', '02', '03', '04', '05', '06',
              '07', '08', '09', '10', '11', '12']
    categories = Category.objects.count()
    products = Products.objects.count()

    today_sales = Sales.objects.filter(
        date_added__year=current_year,
        date_added__month=current_month,
        date_added__day=current_day
    )
    transaction = today_sales.count()
    total_sales = sum(today_sales.values_list('grand_total', flat=True))

    context = {
        'page_title': 'Inicio',
        'categories': categories,
        'products': products,
        'transaction': transaction,
        'total_sales': total_sales,
        'months': months,
        'year_range': range(current_year - 4, current_year + 1),  # ✅ Aquí
        'now': now,  # para usar `now.year` en el template
    }
    return render(request, 'posApp/home.html', context)

@login_required
def monthly_sales_data(request):
    from datetime import datetime
    from .models import salesItems, Expense  
    year = int(request.GET.get('year', datetime.now().year))
    category_id = request.GET.get('category_id', None)

    # Inicializar estructuras
    sales_data = [0] * 12
    expense_data = [0] * 12
    product_sales_by_month = [defaultdict(float) for _ in range(12)]

    items_qs = salesItems.objects.select_related('sale_id', 'product_id') \
        .filter(sale_id__date_added__year=year)

    if category_id:
        items_qs = items_qs.filter(product_id__category_id=category_id)

    for item in items_qs:
        month = item.sale_id.date_added.month - 1
        sales_data[month] += float(item.total)
        product_sales_by_month[month][item.product_id.name] += float(item.total)

    expenses = Expense.objects.filter(expense_date__year=year) \
        .values('expense_date__month') \
        .annotate(total=Sum('amount'))

    for e in expenses:
        month = e['expense_date__month'] - 1
        expense_data[month] = float(e['total'])

    # Convertir defaultdicts a dict para enviar por JSON
    productos_por_mes = [dict(mes) for mes in product_sales_by_month]
    saldo_data = [ventas - gastos for ventas, gastos in zip(sales_data, expense_data)]

    return JsonResponse({
        'labels': [
            'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ],
        'sales': sales_data,
        'expenses': expense_data,
        'saldo': saldo_data,
        'product_sales': productos_por_mes,
        'year': year,
        'year_range': list(range(timezone.now().year - 4, timezone.now().year + 1)),
    })

#
@login_required
def daily_gains_data(request):
    year = int(request.GET.get('year'))
    month = int(request.GET.get('month'))

    days_in_month = monthrange(year, month)[1]
    sales_by_day = [0] * days_in_month
    expenses_by_day = [0] * days_in_month

    sales = Sales.objects.filter(date_added__year=year, date_added__month=month)
    for s in sales:
        day = s.date_added.day - 1
        sales_by_day[day] += float(s.grand_total)

    expenses = Expense.objects.filter(expense_date__year=year, expense_date__month=month)
    for e in expenses:
        day = e.expense_date.day - 1
        expenses_by_day[day] += float(e.amount)

    saldo_by_day = [round(sales_by_day[i] - expenses_by_day[i], 2) for i in range(days_in_month)]

    return JsonResponse({
        'labels': list(range(1, days_in_month + 1)),
        'sales': sales_by_day,
        'expenses': expenses_by_day,
        'saldo': saldo_by_day
    })
    
@login_required
def product_sales_pie_data(request):
    year = int(request.GET.get('year'))
    month = int(request.GET.get('month'))

    items_qs = salesItems.objects.select_related('sale_id', 'product_id') \
        .filter(sale_id__date_added__year=year, sale_id__date_added__month=month)

    product_totals = defaultdict(float)
    for item in items_qs:
        product_totals[item.product_id.name] += float(item.total)

    labels = list(product_totals.keys())
    data = list(product_totals.values())

    return JsonResponse({
        'labels': labels,
        'data': data,
    })




#
def about(request):
    context = {
        'page_title':'About',
    }
    return render(request, 'posApp/about.html',context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def category(request):
    category_list = Category.objects.all()
    context = {
        'page_title': 'Lista de Categorias',
        'category': category_list,
    }
    return render(request, 'posApp/category.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def manage_category(request):
    category = {}
    if request.method == 'GET':
        data =  request.GET
        id = ''
        if 'id' in data:
            id= data['id']
        if id.isnumeric() and int(id) > 0:
            category = Category.objects.filter(id=id).first()
    
    context = {
        'category' : category
    }
    return render(request, 'posApp/manage_category.html',context)

@login_required
def color(request):
    search = request.GET.get('search', '')
    if search:
        color_list = Color.objects.filter(name__icontains=search)
    else:
        color_list = Color.objects.all()
    # category_list = {}
    context = {
        'page_title':'Lista de Colores',
        'color':color_list,
    }
    return render(request, 'posApp/color.html',context)

@login_required
def manage_color(request):
    color = {}
    if request.method == 'GET':
        data =  request.GET
        id = ''
        if 'id' in data:
            id= data['id']
        if id.isnumeric() and int(id) > 0:
            color = Color.objects.filter(id=id).first()
    
    context = {
        'color' : color
    }
    return render(request, 'posApp/manage_color.html',context)


@login_required
def save_color(request):
    data =  request.POST
    resp = {'status':'failed'}
    try:
        if (data['id']).isnumeric() and int(data['id']) > 0 :
            save_color = Color.objects.filter(id = data['id']).update(name=data['name'],status = data['status'])
        else:
            save_color = Color(name=data['name'],status = data['status'])
            save_color.save()
        resp['status'] = 'success'
        messages.success(request, 'Color agregado correctamente.')
    except:
        resp['status'] = 'failed'
    return HttpResponse(json.dumps(resp), content_type="application/json")



@login_required
def delete_color(request):
    data = request.POST
    resp = {'status': ''}
    try:
        # Intentar eliminar la categoría
        Color.objects.get(id=data['id']).delete()
        resp['status'] = 'success'
        messages.success(request, 'Color eliminado.')

    except Exception as e:
        if "restricted foreign keys" in str(e):
            resp['status'] = 'failed'
            resp['message'] = 'No se puede eliminar el color seleccionado porque está relacionado con uno o más productos.'
        else:
            resp['status'] = 'failed'
            resp['message'] = f'Ocurrió un error inesperado: {str(e)}'

    return HttpResponse(json.dumps(resp), content_type="application/json")



""
@login_required
@user_passes_test(lambda u: u.is_superuser)
def payment(request):
    search = request.GET.get('search', '')
    if search:
        color_list = PaymentType.objects.filter(name__icontains=search)
    else:
        color_list = PaymentType.objects.all()
    # category_list = {}
    context = {
        'page_title':'Lista de Tipos de pago',
        'payment':color_list,
    }
    return render(request, 'posApp/payment.html',context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def manage_payment(request):
    payment = {}
    if request.method == 'GET':
        data =  request.GET
        id = ''
        if 'id' in data:
            id= data['id']
        if id.isnumeric() and int(id) > 0:
            payment = PaymentType.objects.filter(id=id).first()
    
    context = {
        'payment' : payment
    }
    return render(request, 'posApp/manage_payment.html',context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def save_payment(request):
    data =  request.POST
    resp = {'status':'failed'}
    try:
        if (data['id']).isnumeric() and int(data['id']) > 0 :
            save_payment = PaymentType.objects.filter(id = data['id']).update(name=data['name'],status = data['status'])
        else:
            save_payment = PaymentType(name=data['name'],status = data['status'])
            save_payment.save()
        resp['status'] = 'success'
        messages.success(request, 'Tipo de pago agregado correctamente.')
    except:
        resp['status'] = 'failed'
    return HttpResponse(json.dumps(resp), content_type="application/json")



@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_payment(request):
    data = request.POST
    resp = {'status': ''}
    try:
        # Intentar eliminar la categoría
        PaymentType.objects.get(id=data['id']).delete()
        resp['status'] = 'success'
        messages.success(request, 'Tipo de pago eliminado.')

    except Exception as e:
        if "restricted foreign keys" in str(e):
            resp['status'] = 'failed'
            resp['message'] = 'No se puede eliminar el tipo de pago seleccionado porque está relacionado con uno o más ventas.'
        else:
            resp['status'] = 'failed'
            resp['message'] = f'Ocurrió un error inesperado: {str(e)}'

    return HttpResponse(json.dumps(resp), content_type="application/json")
""


def calcular_ingresos_netos_por_tipo(start_date, end_date):
    pagos = SalesPayment.objects.filter(
        sale__date_added__date__range=(start_date, end_date)
    ).select_related('sale', 'payment_type')

    ingresos_por_tipo = defaultdict(float)

    # Agrupar pagos por venta
    pagos_por_venta = defaultdict(list)
    for pago in pagos:
        pagos_por_venta[pago.sale_id].append(pago)

    for pagos_venta in pagos_por_venta.values():
        if not pagos_venta:
            continue

        # Vuelto de la venta
        venta = pagos_venta[0].sale
        vuelto = venta.amount_change or 0

        if len(pagos_venta) == 1:
            # Solo un método de pago: se le resta el vuelto directamente
            pago = pagos_venta[0]
            neto = max(pago.amount - vuelto, 0)
            ingresos_por_tipo[pago.payment_type.name] += neto
        else:
            # Varios métodos de pago: se resta el vuelto al mayor
            pagos_venta.sort(key=lambda x: x.amount, reverse=True)
            mayor = pagos_venta[0]
            neto_mayor = max(mayor.amount - vuelto, 0)
            ingresos_por_tipo[mayor.payment_type.name] += neto_mayor

            for pago in pagos_venta[1:]:
                ingresos_por_tipo[pago.payment_type.name] += pago.amount

    return ingresos_por_tipo



@login_required
def cash_register(request):
    # Parámetros del request
    opening_date_start = request.GET.get('opening_date_start')
    opening_date_end = request.GET.get('opening_date_end')
    user_id = request.GET.get('user_id')
    per_page = request.GET.get('per_page', 10)

    # Años y meses disponibles para filtro
    available_years = list(range(2022, datetime.now().year + 1))
    months = list(range(1, 13))

    # Mes y año seleccionados (por defecto actual)
    month = int(request.GET.get('month', now().month))
    year = int(request.GET.get('year', now().year))

    queryset = CashRegister.objects.all().select_related('user')

    # Si no es superusuario, filtrar solo sus cajas
    if not request.user.is_superuser:
        today = now().date()
        queryset = queryset.filter(user=request.user, opening_date__date=today)

    # Filtrar por fecha de apertura
    if opening_date_start:
        queryset = queryset.filter(opening_date__date__gte=opening_date_start)
    else:
        start_of_month = date(year, month, 1)
        end_of_month = date(year, month, monthrange(year, month)[1])
        queryset = queryset.filter(opening_date__date__range=(start_of_month, end_of_month))

    # Filtrar por fecha de cierre
    if opening_date_end:
        queryset = queryset.filter(opening_date__date__lte=opening_date_end)

    # Filtrar por usuario si se envía
    if user_id:
        queryset = queryset.filter(user_id=user_id)

    # Paginación
    paginator = Paginator(queryset.order_by('-opening_date'), per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Rango actual del mes seleccionado
    start_of_month = date(year, month, 1)
    end_of_month = date(year, month, monthrange(year, month)[1])

    # Totales del mes actual
    total_ingresos_mes = Sales.objects.filter(
        date_added__date__range=(start_of_month, end_of_month)
    ).aggregate(total=Sum('grand_total'))['total'] or 0

    total_egresos_mes = Expense.objects.filter(
        expense_date__date__range=(start_of_month, end_of_month)
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Obtener el fin del mes anterior
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    prev_end = date(prev_year, prev_month, monthrange(prev_year, prev_month)[1])

    # Acumulado hasta el fin del mes anterior
    ventas_acumuladas = Sales.objects.filter(
        date_added__date__lte=prev_end
    ).aggregate(total=Sum('grand_total'))['total'] or 0

    egresos_acumulados = Expense.objects.filter(
        expense_date__date__lte=prev_end
    ).aggregate(total=Sum('amount'))['total'] or 0

    saldo_acumulado_hasta_mes_anterior = ventas_acumuladas - egresos_acumulados
    flujo_acumulado_neto = saldo_acumulado_hasta_mes_anterior + total_ingresos_mes - total_egresos_mes

    ingresos_por_tipo_mes = calcular_ingresos_netos_por_tipo(start_of_month, end_of_month)
    ingresos_por_tipo_acumulado = calcular_ingresos_netos_por_tipo(date.min, prev_end)


    # Enriquecer cada caja con sus indicadores
    for caja in page_obj:
        ventas = caja.sales.aggregate(total=Sum('grand_total'))['total'] or 0
        egresos = caja.expenses.aggregate(total=Sum('amount'))['total'] or 0
        caja.ventas_total = ventas
        caja.egresos_total = egresos
        caja.neto = ventas - egresos

    users = User.objects.all() if request.user.is_superuser else []
    today = now().date()  
    opened_today_count = False
    if not request.user.is_superuser:
        opened_today_count = CashRegister.objects.filter(
            user=request.user,
            opening_date__date= today
        ).exists()
        
    context = {
        'payment': page_obj,
        'page_obj': page_obj,
        'available_years': available_years,
        'months': months,
        'users': users,
        'base_url': urlencode({k: v for k, v in request.GET.items() if k != 'page'}),
        'saldo_mes_anterior': saldo_acumulado_hasta_mes_anterior,
        'ingresos_por_tipo_mes': ingresos_por_tipo_mes.items(),
        'ingresos_por_tipo_acumulado': ingresos_por_tipo_acumulado.items(),
        'egresos_acumulados': egresos_acumulados, 
        'total_ingresos_mes': total_ingresos_mes,
        'total_egresos_mes': total_egresos_mes,
        'flujo_acumulado_neto': flujo_acumulado_neto,
        'month': month,
        'year': year,
        'opened_today_count': opened_today_count,
        'request_get': request.GET,
    }
    return render(request, 'posApp/cashRegister/cash_register.html', context)


from collections import defaultdict
from decimal import Decimal

@login_required
def cash_register_detail(request, pk):
    cash_register = get_object_or_404(CashRegister, pk=pk)
    expenses = cash_register.expenses.all()
    cash_register_sales = CashRegisterSales.objects.filter(cash_register=cash_register)
    sales = [crs.sale for crs in cash_register_sales]

    expense_total = expenses.aggregate(total=Sum('amount'))['total'] or 0
    income_total = sum(s.grand_total for s in sales)
    final_total = income_total - expense_total

    # === Ingresos por producto ===
    ingresos_por_producto = (
        salesItems.objects
        .filter(sale_id__in=sales)
        .values(nombre=F('product_id__name'))
        .annotate(
            total_monto=Sum('total'),
            total_cantidad=Sum('qty')
        )
        .order_by('-total_monto')
    )
    pagos_por_tipo = defaultdict(Decimal)

    for sale in sales:
        pagos = list(sale.sales_payments.all())
        vuelto = sale.amount_change

        if not pagos:
            continue

        # Buscar el pago con mayor monto
        pago_max = max(pagos, key=lambda p: p.amount)

        for pago in pagos:
            ingreso_real = pago.amount

            if pago == pago_max:
                ingreso_real -= vuelto  # Solo a este le restamos el vuelto

            pagos_por_tipo[pago.payment_type.name] += Decimal(ingreso_real)

    # Convertimos a lista para usar en template
    ingresos_por_tipo_pago = [
        {'tipo': tipo, 'monto': float(round(monto, 2))}
        for tipo, monto in pagos_por_tipo.items()
    ]
    ingresos_por_tipo_pago.sort(key=lambda x: -x['monto'])  # Orden descendente por monto
    
    context = {
        'cash_register': cash_register,
        'expenses': expenses,
        'sales': sales,
        'income_total': income_total,
        'expense_total': expense_total,
        'final_total': final_total,
        'ingresos_por_producto': ingresos_por_producto,
        'ingresos_por_tipo_pago': ingresos_por_tipo_pago,
    }
    return render(request, 'posApp/cashRegister/cash_register_detail.html', context)

@login_required
def manage_cash_register(request):
    cash_register = {}
    if request.user.is_superuser:
        users = User.objects.all()
    else:
        users = User.objects.filter(id=request.user.id)
    if request.method == 'GET':
        data = request.GET
        id = ''
        if 'id' in data:
            id = data['id']
        if id.isnumeric() and int(id) > 0:
            cash_register = CashRegister.objects.filter(id=id).first()

    context = {
        'cash_register': cash_register,
        'users': users  
    }
    return render(request, 'posApp/cashRegister/manage_cash_register.html', context)

@login_required
def save_cash_register(request):
    data = request.POST
    resp = {'status': 'failed'}
    try:
        user_id = data.get('user_id')
        user = None
        if user_id and user_id.isdigit():
            try:
                user = User.objects.get(id=int(user_id))
            except User.DoesNotExist:
                messages.error(request, 'El usuario seleccionado no existe.')
                return HttpResponse(json.dumps(resp), content_type="application/json")

        if (data['id']).isnumeric() and int(data['id']) > 0:
            try:
                cash_reg = CashRegister.objects.get(id=int(data['id']))
                cash_reg.user = user

                # Si se marcó el switch para reabrir
                if data.get('reopen_register') == '1':
                    cash_reg.close_date = None  # Reabrir la caja

                cash_reg.save()
                resp['status'] = 'success'
                messages.success(request, 'Caja registradora actualizada correctamente.')
            except CashRegister.DoesNotExist:
                resp['status'] = 'failed'
                messages.error(request, 'La caja registradora especificada no existe.')
        else:
            # Crear nueva caja
            cash_reg = CashRegister(
                user=user
            )
            cash_reg.save()
            resp['status'] = 'success'
            messages.success(request, 'Caja registradora agregada correctamente.')
    except Exception as e:
        resp['status'] = 'failed'
        messages.error(request, f'Ocurrió un error al guardar la caja registradora: {e}')
    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_cash_register(request):
    if request.method == "POST":
        cash_register_id = request.POST.get("id")
        try:
            cash_register = CashRegister.objects.get(id=cash_register_id)

            if cash_register.sales.exists():
                return JsonResponse({
                    "status": "failed",
                    "message": "No se puede eliminar la caja porque tiene ventas asociadas."
                })

            cash_register.delete()
            return JsonResponse({"status": "success"})

        except CashRegister.DoesNotExist:
            return JsonResponse({"status": "failed", "message": "Caja no encontrada."})

    return JsonResponse({"status": "failed", "message": "Método no permitido."})

@login_required
def close_cash_register_modal(request):
    cash_register = {}
    expense_total = {}
    income_total = {}
    final_total = {}

    if request.method == 'GET':
        data = request.GET
        id = ''
        if 'id' in data:
            id = data['id']
        if id.isnumeric() and int(id) > 0:
            cash_register = CashRegister.objects.filter(id=id).first()
            expenses = cash_register.expenses.all()
            cash_register_sales = CashRegisterSales.objects.filter(cash_register=cash_register)
            sales = [crs.sale for crs in cash_register_sales]
            expense_total = expenses.aggregate(total=Sum('amount'))['total'] or 0
            # suma de ingresos (grand_total de cada venta)
            income_total = sum(s.grand_total for s in sales)
            # monto final = inicial + ingresos – gastos
            final_total = income_total - expense_total


    context = {
        'cash_register': cash_register,
        'income_total': income_total,
        'expense_total': expense_total,
        'final_total': final_total,
    }
    return render(request, 'posApp/cashRegister/close_cash_register.html', context)

@login_required
def cash_register_expenses(request):

    data = request.POST
    resp = {'status': 'failed'}  
    try:
        cash_register_id = data.get('cash_register_id')
        if not cash_register_id or not cash_register_id.isdigit() or int(cash_register_id) <= 0:
            resp['message'] = 'ID de caja registradora inválido.'
            messages.error(request, resp['message'])
            return HttpResponse(json.dumps(resp), content_type="application/json", status=400)

        cash_reg = get_object_or_404(CashRegister, id=int(cash_register_id))

        expense_description = data.get('description')
        expense_amount = data.get('amount')
        
        try:
            expense_amount = float(expense_amount)
        except ValueError:
            resp['message'] = 'Monto inválido.'
            messages.error(request, resp['message'])
            return HttpResponse(json.dumps(resp), content_type="application/json", status=400)

        Expense.objects.create(
            cash_register=cash_reg,
            description=expense_description,
            amount=expense_amount,
            expense_date=timezone.now(),
        )

        resp['status'] = 'success'
        resp['message'] = 'Gasto registrado correctamente.'
        messages.success(request, resp['message']) 
        return HttpResponse(json.dumps(resp), content_type="application/json")

    except Exception as e:
        resp['message'] = f'Ocurrió un error al registrar el gasto: {e}'
        messages.error(request, resp['message'])
    return HttpResponse(json.dumps(resp), content_type="application/json", status=500)
    
    
@login_required
def cash_register_expenses_modal(request):
    cash_register = {}
    if request.method == 'GET':
        data = request.GET
        id = ''
        if 'id' in data:
            id = data['id']
        if id.isnumeric() and int(id) > 0:
            cash_register = CashRegister.objects.filter(id=id).first()

    context = {
        'cash_register': cash_register,
    }
    return render(request, 'posApp/cashRegister/cash_register_expenses.html', context)

@login_required
def delete_cash_register_expenses(request):
    data = request.POST
    resp = {'status': ''}
    try:
        Expense.objects.get(id=data['id']).delete()
        resp['status'] = 'success'
        messages.success(request, 'Gasto Eliminado.')

    except Exception as e:
        if "restricted foreign keys" in str(e):
            resp['status'] = 'failed'
            resp['message'] = 'No se puede eliminar la caja seleccionada porque está relacionado con uno o más ventas.'
        else:
            resp['status'] = 'failed'
            resp['message'] = f'Ocurrió un error inesperado: {str(e)}'

    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
def close_cash_register(request):
    data = request.POST
    resp = {'status': 'failed'}
    try:
        if (data['id']).isnumeric() and int(data['id']) > 0:
            # Editar una caja registradora existente
            try:
                cash_reg = CashRegister.objects.get(id=int(data['id']))
                cash_reg.close_date = timezone.now()
                cash_reg.save()
                resp['status'] = 'success'
                messages.success(request, 'Caja registradora Cerrada correctamente.')
            except CashRegister.DoesNotExist:
                resp['status'] = 'failed'
                messages.error(request, 'La caja registradora especificada no existe.')

    except Exception as e:
        resp['status'] = 'failed'
        resp['message'] = f"Ocurrió un error al cerrar la caja registradora : {e}"
        messages.error(request, f"Ocurrió un error al cerrar la caja registradora : {e}") 
    return JsonResponse(resp)


##

@login_required
def size(request):
    search = request.GET.get('search', '')
    if search:
        size_list = Size.objects.filter(name__icontains=search)
    else:
        size_list = Size.objects.all()
    # category_list = {}
    context = {
        'page_title':'Lista de Tallas',
        'size':size_list,
    }
    return render(request, 'posApp/size.html',context)

@login_required
def manage_size(request):
    size = {}
    if request.method == 'GET':
        data =  request.GET
        id = ''
        if 'id' in data:
            id= data['id']
        if id.isnumeric() and int(id) > 0:
            size = Size.objects.filter(id=id).first()
    
    context = {
        'size' : size
    }
    return render(request, 'posApp/manage_size.html',context)


@login_required
def save_size(request):
    data =  request.POST
    resp = {'status':'failed'}
    try:
        if (data['id']).isnumeric() and int(data['id']) > 0 :
            save_size = Size.objects.filter(id = data['id']).update(name=data['name'],status = data['status'])
        else:
            save_size = Size(name=data['name'],status = data['status'])
            save_size.save()
        resp['status'] = 'success'
        messages.success(request, 'Talla agregado correctamente.')
    except:
        resp['status'] = 'failed'
    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
def delete_size(request):
    data = request.POST
    resp = {'status': ''}
    try:
        # Intentar eliminar la categoría
        Size.objects.get(id=data['id']).delete()
        resp['status'] = 'success'
        messages.success(request, 'Talla eliminada.')

    except Exception as e:
        if "restricted foreign keys" in str(e):
            resp['status'] = 'failed'
            resp['message'] = 'No se puede eliminar la talla seleccionada porque está relacionado con uno o más productos.'
        else:
            resp['status'] = 'failed'
            resp['message'] = f'Ocurrió un error inesperado: {str(e)}'

    return HttpResponse(json.dumps(resp), content_type="application/json")



@login_required
def save_category(request):
    data =  request.POST
    resp = {'status':'failed'}
    try:
        if (data['id']).isnumeric() and int(data['id']) > 0 :
            save_category = Category.objects.filter(id = data['id']).update(name=data['name'], description = data['description'],status = data['status'])
        else:
            save_category = Category(name=data['name'], description = data['description'],status = data['status'])
            save_category.save()
        resp['status'] = 'success'
        messages.success(request, 'Categoria agregada correctamente.')
    except:
        resp['status'] = 'failed'
    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_category(request):
    data = request.POST
    resp = {'status': ''}
    try:
        # Intentar eliminar la categoría
        Category.objects.get(id=data['id']).delete()
        resp['status'] = 'success'
        messages.success(request, 'Categoría eliminada.')

    except Exception as e:
        if "restricted foreign keys" in str(e):
            resp['status'] = 'failed'
            resp['message'] = 'No se puede eliminar la categoría porque está relacionada con uno o más productos.'
        else:
            resp['status'] = 'failed'
            resp['message'] = f'Ocurrió un error inesperado: {str(e)}'

    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
@user_passes_test(lambda u: u.is_superuser)
def products(request):
    search = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    per_page = request.GET.get('per_page', 10)

    # Filtrado
    product_list = Products.objects.all()
    if search:
        product_list = product_list.filter(name__icontains=search)
    if category_filter:
        product_list = product_list.filter(category_id=category_filter)
    if status_filter:
        product_list = product_list.filter(status=status_filter)

    total_products = product_list.count()

    # Paginación
    paginator = Paginator(product_list, per_page)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)

    # Construir base_url sin el parámetro "page"
    filters = request.GET.copy()
    if 'page' in filters:
        filters.pop('page')
    base_url = urlencode(filters)

    context = {
        'page_title': 'Lista de Productos',
        'products': products_page,
        'total_products': total_products,
        'category_filter': category_filter,
        'categories': Category.objects.all(),
        'base_url': base_url,
    }
    return render(request, 'posApp/products/products.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def manage_products(request):
    product = {}
    features = []
    categories = Category.objects.filter(status=1).all()
    colors = Color.objects.all()
    sizes = Size.objects.all()

    if request.method == 'GET':
        data = request.GET
        id = ''
        if 'id' in data:
            id = data['id']
        if id.isnumeric() and int(id) > 0:
            product = Products.objects.filter(id=id).first()
            if product:
                features = product.features.all()

    context = {
        'product': product,
        'features': features,
        'categories': categories,
        'colors': colors,
        'sizes': sizes,
    }
    return render(request, 'posApp/products/manage_product.html', context)

def test(request):
    categories = Category.objects.all()
    context = {
        'categories' : categories
    }
    return render(request, 'posApp/test.html',context)

@transaction.atomic
@login_required
def save_product(request):
    data = request.POST
    resp = {'status': 'failed'}

    deleted_features = data.get('deleted_features', '').split(',')
    deleted_features = [int(feature_id) for feature_id in deleted_features if feature_id.isdigit()]

    # Eliminar las características marcadas como eliminadas
    ProductFeature.objects.filter(id__in=deleted_features).delete()

    try:
        # Manejo del ID
        id = data.get('id', '')
        id = int(id) if id.isnumeric() else None

        # Validar datos necesarios
        if not data.get('code') or not data.get('name') or not data.get('price'):
            resp['msg'] = "Código, nombre y precio son campos obligatorios."
            return HttpResponse(json.dumps(resp), content_type="application/json")

        # Validar precios
        try:
            price = float(data['price'].replace(',', '.'))
            p_mayor = float(data['p_mayor'].replace(',', '.'))
        except ValueError:
            resp['msg'] = "Formato de precio no válido. Usa números y puntos."
            return HttpResponse(json.dumps(resp), content_type="application/json")

        # Validar categoría
        category_id = data.get('category_id')
        category = Category.objects.filter(id=category_id).first() if category_id else None
        if not category:
            resp['msg'] = "Categoría seleccionada no es válida."
            return HttpResponse(json.dumps(resp), content_type="application/json")

        # Verificar duplicados
        if id:
            duplicate_check = Products.objects.exclude(id=id).filter(code=data['code']).exists()
        else:
            duplicate_check = Products.objects.filter(code=data['code']).exists()

        if duplicate_check:
            resp['msg'] = "El código del producto ya existe en la base de datos."
            return HttpResponse(json.dumps(resp), content_type="application/json")

        # Guardar o actualizar producto
        if id:
            # Actualización de producto existente
            product = Products.objects.get(id=id)
            product.code = data['code']
            product.category_id = category
            product.name = data['name']
            product.description = data['description']
            product.price = price
            product.p_mayor = p_mayor
            product.stock = int(data['stock'])
            product.status = int(data['status'])
        else:
            # Crear nuevo producto
            product = Products.objects.create(
                code=data['code'],
                category_id=category,
                name=data['name'],
                description=data['description'],
                price=price,
                p_mayor=p_mayor,
                stock=int(data['stock']),
                status=int(data['status']),
            )

        if 'image' in request.FILES:
            new_image = request.FILES['image']
            fs = FileSystemStorage(location='media/products')
            filename = fs.save(new_image.name, new_image)
            image_url = 'media/products/' + filename
            # Si ya existe una imagen anterior, eliminarla
            if product.image:
                if os.path.isfile(product.image):
                    os.remove(product.image)
            # Asignar la nueva imagen al producto
            product.image = image_url

        # Manejo de características (ProductFeature)
        ProductFeature.objects.filter(product=product).delete()  # Elimina características previas
        feature_colors = data.getlist('feature_color[]')
        feature_sizes = data.getlist('feature_size[]')
        feature_stocks = data.getlist('feature_stock[]')

        total_feature_stock = 0
        for color_id, size_id, stock in zip(feature_colors, feature_sizes, feature_stocks):
            stock = int(stock)
            total_feature_stock += stock
            color = Color.objects.filter(id=color_id).first()
            size = Size.objects.filter(id=size_id).first()

            if color and size:
                ProductFeature.objects.create(product=product, color=color, size=size, stock=stock)

        if total_feature_stock > product.stock:
            raise ValueError("El stock total de las características no puede superar el stock general del producto.")

        product.save() 
        resp['status'] = 'success'
        resp['msg'] = "Producto guardado correctamente."
    except Exception as e:
        if "UNIQUE" in str(e):
            resp['msg'] = "No se puede guardar el mismo color y talla del producto"
        else:
            print(f"Error al guardar el producto: {e}")
            resp['msg'] = f"Error al guardar el producto: {str(e)}"

    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
def upload_file(request):
    media_path = os.path.join(settings.MEDIA_ROOT)
    selected_directory = request.POST.get('directory', '') 
    selected_directory_path = os.path.join(media_path,"products")
    print(selected_directory)
    # Crea la carpeta si no existe
    #os.makedirs(selected_directory_path, exist_ok=True)

    if request.method == 'POST':
        file = request.FILES.get('file')
        # Obtiene la extensión del archivo
        extension = os.path.splitext(file.name)[1]
        # Crea el nuevo nombre del archivo
        new_file_name = f"{selected_directory}{extension}"
        file_path = os.path.join(selected_directory_path, new_file_name)
        with open(file_path, 'wb') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

    return redirect(request.META.get('HTTP_REFERER'))


@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_product(request):
    data =  request.POST
    resp = {'status':''}
    try:
        product = Products.objects.get(id=data['id'])
        if product.image:
       
            if os.path.isfile(product.image):
                os.remove(product.image)
        product.delete()
        resp['status'] = 'success'
        messages.success(request, 'Producto eliminado.')
    except Exception as e:
        if "restricted foreign keys" in str(e):
            resp['status'] = 'failed'
            resp['message'] = 'No se puede eliminar el Producto por que esta relacionado a una o varias ventas'
        else:
            resp['status'] = 'failed'
            resp['message'] = f'Ocurrió un error inesperado: {str(e)}'
        
    return HttpResponse(json.dumps(resp), content_type="application/json")

#Solo Deja registrar si la caja esta abierta y si la fecha de apertura es la fecha actual 
@login_required
def pos(request):
    products = Products.objects.filter(status=1)
    
    today = now().date()  
    if request.user.is_superuser:
        cash_register = CashRegister.objects.filter(
            close_date__isnull=True,
            opening_date__date=today
        )
    else:
        cash_register = CashRegister.objects.filter(
            close_date__isnull=True,
            user=request.user,
            opening_date__date=today
        )

    payment = PaymentType.objects.all()
    mostrar_modal = not cash_register.exists()  

    product_json = []
    for product in products:
        features = product.features.all()
        feature_data = [
            {
                'id': feature.id,
                'color': feature.color.name,
                'size': feature.size.name,
                'stock': feature.stock
            }
            for feature in features
        ]
        product_json.append({
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'stock': product.stock,
            'features': feature_data
        })

    context = {
        'page_title': "Punto de venta",
        'products': products,
        'payment': payment,
        'cash_registers': cash_register,
        'product_json': json.dumps(product_json),
        'mostrar_modal': mostrar_modal
    }
    return render(request, 'posApp/pos/pos.html', context)


@login_required
def checkout_modal(request):
    grand_total = 0
    payment = PaymentType.objects.filter(status=1).all()
    if 'grand_total' in request.GET:
        grand_total = request.GET['grand_total']
    context = {
        'grand_total' : grand_total,
        'payment': payment,
    }
    return render(request, 'posApp/pos/checkout.html',context)

@login_required
def save_pos(request):
    resp = {'status': 'failed', 'msg': ''}
    data = request.POST
    pref = datetime.now().year + datetime.now().year

    try:
        # Generar código único
        i = 1
        while True:
            code = '{:0>5}'.format(i)
            i += 1
            full_code = str(pref) + str(code)
            if not Sales.objects.filter(code=full_code).exists():
                break

        # Crear venta
        sale = Sales.objects.create(
            code=full_code,
            sub_total=data['sub_total'],
            descuento=data['descuento'],
            tax=data['tax'],
            tax_amount=data['tax_amount'],
            grand_total=data['grand_total'],
            tendered_amount=data['tendered_amount'],
            amount_change=data['amount_change'],
        )

        # Registrar productos vendidos
        for i, product_id in enumerate(data.getlist('product_id[]')):
            product = Products.objects.get(id=product_id)
            qty = int(data.getlist('qty[]')[i])
            price = float(data.getlist('price[]')[i])
            total = qty * price

            feature_id = data.getlist('feature_id[]')[i] if 'feature_id[]' in data else None
            feature = ProductFeature.objects.filter(id=feature_id).first() if feature_id else None

            if product.category_id.name.strip().upper() not in ['PARQUE']:
                product.stock -= qty
                product.save()

            if feature:
                feature.stock -= qty
                feature.save()

            salesItems.objects.create(
                sale_id=sale,
                product_id=product,
                feature_id=feature,
                qty=qty,
                price=price,
                total=total
            )

        # Registrar pagos múltiples (usando arrays)
        try:
            payment_methods = json.loads(data.get('payment_methods', '[]'))
        except json.JSONDecodeError:
            payment_methods = []

        for pay in payment_methods:
            try:
                payment_type = PaymentType.objects.get(id=pay['payment_type'])
                amount = float(pay['amount'])
                if amount > 0:
                    SalesPayment.objects.create(sale=sale, payment_type=payment_type, amount=amount)
            except (PaymentType.DoesNotExist, ValueError, KeyError):
                continue  # ignora pagos inválidos


        # Registrar en caja
        cash_register_id = data.get('cash_register_id')
        if cash_register_id:
            cash_register = CashRegister.objects.filter(id=cash_register_id).first()
            if cash_register:
                CashRegisterSales.objects.create(cash_register=cash_register, sale=sale)

        # Desactivar productos sin stock
        Products.objects.filter(stock=0).update(status=0)

        resp['status'] = 'success'
        resp['sale_id'] = sale.pk
        messages.success(request, "Registro de venta exitoso")

    except Exception as e:
        resp['msg'] = str(e)
        print("Error inesperado:", e)

    return JsonResponse(resp)

@csrf_exempt
def generate_qr(request):
    if request.method == 'POST':
        product_id = request.POST.get('id')
        product = Products.objects.get(pk=product_id)

        # Convertir el objeto del producto a string
        idp = str(product.pk)
        pro = str(product.price)

        # Generar el QR
        img = qrcode.make(idp+"- S/. "+pro)

        # Guardar el QR en un archivo temporal
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        image_png = buffer.getvalue()
        buffer.close()
        for file in os.listdir('media/static/qr_codes/'):
                    os.remove(os.path.join('media/static/qr_codes/', file))

        # Crear un archivo Django con el QR
        qr_image = ContentFile(image_png)
        file_path = default_storage.save('static/qr_codes/' + product_id + '.png', qr_image)
        
        qr_url = default_storage.url(file_path)
        return JsonResponse({'status': 'success', 'qr_url': qr_url})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def save_qr(request):
    qr_code = request.GET.get('qr_code')
    product = Products.objects.get(code=qr_code)
    return JsonResponse({'product_id': product.id})



def clean_get_params(params):
    """
    Elimina listas y entradas vacías del QueryDict.
    Convierte listas de un solo elemento en valores simples.
    """
    clean = {}
    for key in params:
        value = params.getlist(key)
        if value:
            clean[key] = value[0]  # solo tomamos el primer valor
    return clean

@login_required
def salesList(request):
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '') 
    date_to = request.GET.get('date_to', '')
    payment_type_id = request.GET.get('payment_type_id', '')
    user_id = request.GET.get('user_id', '')
    per_page = int(request.GET.get('per_page', 10))
    page_number = request.GET.get('page', 1)
    today = now().date()  

    sales = Sales.objects.all()

    if search_query:
        sales = sales.filter(Q(code__icontains=search_query))

    try:
        date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
        sales = sales.filter(date_added__date__gte=date_from_dt)
    except ValueError:
        pass

    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
            sales = sales.filter(date_added__date__lte=date_to_dt)
        except ValueError:
            pass

    if payment_type_id:
        sales = sales.filter(sales_payments__payment_type_id=payment_type_id).distinct()

    if user_id:
        sales = sales.filter(cashregistersales__cash_register__user_id=user_id)

    # Filtrar ventas según el usuario
    if request.user.is_superuser:
        filtered_sales = sales.distinct().order_by('-id') 
    else:
        filtered_sales = sales.filter(
            cashregister__user=request.user,
            date_added__date=today 
        ).distinct().order_by('-id')

    sale_data = []
    for sale in filtered_sales:
        data = {}

        for field in sale._meta.get_fields(include_parents=False):
            if field.related_model is None:
                data[field.name] = getattr(sale, field.name)

        # Métodos de pago
        data['payment_methods'] = [
            {
                'type': pay.payment_type.name,
                'amount': format(pay.amount, '.2f')
            } for pay in sale.sales_payments.all()
        ]

        # Items
        data['items'] = salesItems.objects.filter(sale_id=sale).all()
        data['item_count'] = len(data['items'])

        # Caja relacionada
        cash_register_sale = sale.cashregistersales_set.first()
        if cash_register_sale:
            cash_register = cash_register_sale.cash_register
            data['username'] = cash_register.user.username if cash_register.user else "—"
            data['opening_date'] = cash_register.opening_date
        else:
            data['username'] = "—"
            data['opening_date'] = "—"

        sale_data.append(data)

    # Paginación
    paginator = Paginator(sale_data, per_page)
    page_obj = paginator.get_page(page_number)

    # Para filtros
    payment_types = PaymentType.objects.all()
    users = User.objects.filter(cashregister__isnull=False).distinct()
    today = datetime.now()

    # Limpiar base_url
    from urllib.parse import urlencode
    def clean_get_params(params):
        clean = {}
        for key in params:
            value = params.getlist(key)
            if value:
                clean[key] = value[0]
        return clean

    base_url = urlencode(clean_get_params(request.GET), doseq=True)

    context = {
        'page_title': 'Transacciones',
        'sale_data': page_obj.object_list,
        'page_obj': page_obj,
        'base_url': base_url,
        'payment_types': payment_types,
        'users': users,
        'date_from': date_from,
        'today': datetime.now().date().strftime('%Y-%m-%d'),
    }
    return render(request, 'posApp/sales.html', context)


def expense_list(request):
    today = now().date()
    expenses = Expense.objects.all()

    # Filtro por permisos
    if not request.user.is_superuser:
        expenses = expenses.filter(
            cash_register__user=request.user,
            expense_date__date=today
        )

    # Filtros GET
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    user_id = request.GET.get('user_id')
    cash_register_id = request.GET.get('payment_type_id')  # "Caja" en tu formulario

    if date_from:
        expenses = expenses.filter(expense_date__date__gte=date_from)
    if date_to:
        expenses = expenses.filter(expense_date__date__lte=date_to)
    if user_id:
        expenses = expenses.filter(cash_register__user__id=user_id)
    if cash_register_id:
        expenses = expenses.filter(cash_register__id=cash_register_id)

    # Paginación
    per_page = request.GET.get('per_page', 10)
    paginator = Paginator(expenses.order_by('-expense_date'), per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Preparar usuarios y cajas para los filtros
    users = User.objects.all()
    payment_types = CashRegister.objects.all()

    context = {
        'page_obj': page_obj,
        'expense_data': page_obj.object_list,
        'users': users,
        'payment_types': payment_types,
        'date_from': date_from,
        'date_to': date_to,
        'base_url': request.GET.urlencode().replace(f"&page={page_number}", "") if page_number else request.GET.urlencode()
    }
    return render(request, 'posApp/expenses.html', context)



@login_required
def receipt(request):
    id = request.GET.get('id')
    sales = Sales.objects.filter(id=id).first()
    print_ticket = request.GET.get('print_ticket') == '1'
    logo_url = request.build_absolute_uri('/media/products/logo.png')

    transaction = {}
    for field in Sales._meta.get_fields():
        if field.related_model is None:
            transaction[field.name] = getattr(sales, field.name)
    
    if 'tax_amount' in transaction:
        transaction['tax_amount'] = format(float(transaction['tax_amount']))

    ItemList = salesItems.objects.filter(sale_id=sales).all()
    
    salesPayments = SalesPayment.objects.filter(sale=sales)

    context = {
        'logo_url': logo_url,
        "transaction": transaction,
        "salesItems": ItemList,
        "salesPayments": salesPayments,
        "print_ticket": print_ticket,  
    }

    return render(request, 'posApp/receipt.html', context)
@login_required
def receipt_pdf(request):
    sale_id = request.GET.get('id')
    sale = Sales.objects.filter(id=sale_id).first()
    if not sale:
        return HttpResponse("Venta no encontrada", status=404)

    items = salesItems.objects.filter(sale_id=sale)
    payments = SalesPayment.objects.filter(sale=sale)

    # Parámetros de diseño
    ticket_width = 80 * mm
    line_height = 4 * mm
    top_margin = -1 * mm
    bottom_margin = -4 * mm

    # Calcular líneas fijas y dinámicas
    fixed_lines = 24  # logo+titulos+separadores+datos+headers+total+pie etc.
    num_item_lines = items.count()
    num_payment_lines = payments.count()
    total_lines = fixed_lines + num_item_lines + num_payment_lines 

    # Altura dinámica
    ticket_height = top_margin + bottom_margin + total_lines * line_height

    # Crear canvas en memoria
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=(ticket_width, ticket_height))
    y = ticket_height - top_margin

    # Helpers de dibujo
    def draw_center(text, size=9, move=1):
        nonlocal y
        p.setFont("Courier-Bold", size)
        p.drawCentredString(ticket_width / 2, y, text)
        y -= line_height * move

    def draw_left(text, size=9, move=1):
        nonlocal y
        p.setFont("Courier-Bold", size)
        p.drawString(5 * mm, y, text)
        y -= line_height * move
    
    def draw_left_(text, size=9, move=1):
        nonlocal y
        p.setFont("Courier", size)
        p.drawString(5 * mm, y, text)
        y -= line_height * move
        
    def draw_right(text, size=9, move=1):
        nonlocal y
        p.setFont("Courier", size)
        p.drawRightString(ticket_width - 5 * mm, y, text)
        y -= line_height * move
        
    def draw_right_m(text, size=9, move=1):
        nonlocal y
        p.setFont("Courier-Bold", size)
        p.drawRightString(ticket_width - 5 * mm, y, text)
        y -= line_height * move

    def draw_sep():
        draw_left("-" * 41, size=8, move=1)

    # Logo centrado
    try:
        logo = ImageReader('media/products/logo.png')
        logo_w = 30 * mm
        logo_h = 15 * mm
        p.drawImage(logo, (ticket_width - logo_w) / 2, y - logo_h, width=logo_w, height=logo_h)
        y -= logo_h + line_height
    except Exception:
        draw_center("LOGO NO DISPONIBLE", size=8)

    # Títulos
    draw_center("Parque de Aventuras Santo Domingo", size=8)
    draw_center("Boleta de Venta", size=8)
    draw_center(f"Código de Venta: {sale.code}", size=8)
    draw_sep()

    # Datos fecha/hora y contacto
    draw_left(f"Fecha: {sale.date_added.strftime('%d/%m/%Y')}", size=8)
    draw_left(f"Hora:  {sale.date_added.strftime('%H:%M')}", size=8)
    draw_left("RUC:  1010101010", size=8)
    draw_left("Tel:  942352219", size=8)
    draw_sep()

    # Cabecera de items
    draw_left("Producto", size=9, move=0)
    draw_right_m("Importe", size=9, move=1)

    # Items
    for item in items:
        name = item.product_id.name[:20]
        qty_price = f"{item.qty} x S/ {item.total/item.qty:.2f}"
        p.setFont("Courier", 8)
        p.drawString(5 * mm, y, name)
        p.drawRightString(ticket_width - 5 * mm, y, qty_price)
        y -= line_height

    draw_sep()

    # Total
    draw_left("Total:", size=8, move=0)
    draw_right(f"S/ {sale.grand_total:.2f}", size=8, move=1)
    draw_sep()

    # Métodos de Pago
    draw_left("Métodos de Pago:", size=8)
    for pmt in payments:
        draw_left_(f"{pmt.payment_type.name}", size=8, move=0)
        draw_right(f"S/ {pmt.amount:.2f}", size=8, move=1)

    draw_sep()

    # Recibido / Vuelto
    draw_left("Recibido:", size=8, move=0)
    draw_right(f"S/ {sale.tendered_amount:.2f}", size=8, move=1)
    draw_left("Vuelto:", size=8, move=0)
    draw_right(f"S/ {sale.amount_change:.2f}", size=8, move=1)
    draw_sep()

    # Pie
    draw_center("¡Gracias por su visita!", size=8)

    p.showPage()
    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_sale(request):
    resp = {'status': 'failed', 'msg': ''}
    id = request.POST.get('id')
    restore_stock = request.POST.get('restore_stock', 'false').lower() == 'true'  # Leer el parámetro de restauración
    try:
        if restore_stock:
            # Restaurar stock de los items antes de eliminar la venta
            sale_items = salesItems.objects.filter(sale_id=id)
            
            for item in sale_items:
                product = item.product_id
                if product.category_id.name.strip().upper() not in ['PARQUE']:
                    product.stock += item.qty

                    if product.status == 0 and product.stock > 0:
                        product.status = 1  
                    product.save()
                
                    # Restaurar el stock del feature si aplica
                    if item.feature_id:
                        feature = item.feature_id
                        feature.stock += item.qty
                        feature.save()
        
        # Eliminar la venta y los items asociados
        Sales.objects.filter(id=id).delete()
        
        resp['status'] = 'success'
        if restore_stock:
            messages.success(request, 'Historial de venta eliminado y stock restaurado.')
        else:
            messages.success(request, 'Historial de venta eliminado sin restaurar el stock.')
    except Exception as e:
        resp['msg'] = f"Ocurrió un error: {str(e)}"
        print("Unexpected error:", e)
    
    return HttpResponse(json.dumps(resp), content_type='application/json')
