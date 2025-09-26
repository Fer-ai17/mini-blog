from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Order, OrderItem
from .cart import Cart
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from .forms import ProductForm
from django.urls import reverse_lazy
from .utils import convert_currency as convert_currency, format_price
from django.http import HttpResponseRedirect


def change_currency(request, code):
    """Cambia la moneda - solo permite COP y USD"""
    valid_currencies = ["COP", "USD"]
    code = code.upper()
    
    if code in valid_currencies:
        request.session["currency"] = code
        request.session["currency_manual"] = True
        print(f"✅ Moneda cambiada a: {code}")
    else:
        request.session["currency"] = "COP"
        print(f"⚠️ Moneda no válida, usando COP por defecto")
    
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

@staff_member_required
def admin_dashboard(request):
    total_products = Product.objects.count()
    out_of_stock = Product.objects.filter(stock=0).count()
    total_orders = Order.objects.count()
    last_orders = Order.objects.order_by("-created_at")[:5]

    context = {
        "total_products": total_products,
        "out_of_stock": out_of_stock,
        "total_orders": total_orders,
        "last_orders": last_orders,
    }
    return render(request, "store/admin_dashboard.html", context)

@staff_member_required
def admin_dashboard_products(request):
    products = Product.objects.all().order_by("-created_at")
    return render(request, "store/admin_dashboard_products.html", {"products": products})


@staff_member_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect("admin_dashboard")
    else:
        form = ProductForm(instance=product)
    return render(request, "store/edit_product.html", {"form": form, "product": product})


@staff_member_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return redirect("admin_dashboard")

@staff_member_required
def order_list(request):
    orders = Order.objects.all().order_by("-created_at")
    return render(request, "store/order_list.html", {"orders": orders})


@staff_member_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, "store/order_detail.html", {"order": order})

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    currency = request.session.get("currency", "COP")
    if currency not in ["COP", "USD"]:
        currency = "COP"
    
    locale = "es_CO" if currency == "COP" else "en_US"
    
    # Conversión simple
    if currency == "COP":
        local_price = product.price
    else:
        local_price = convert_currency(product.price, "COP", "USD")
    
    context = {
        "product": product,
        "converted_price": format_price(local_price, currency, locale),
        "base_price": format_price(product.price, "COP", "es_CO"),
        "currency": currency,
    }
    return render(request, "store/product_detail.html", context)

@staff_member_required
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        new_status = request.POST.get("status")
        order.status = new_status
        order.save()
        return redirect("order_detail", pk=order.pk)
    return render(request, "store/update_order_status.html", {"order": order})

def get_converted_cart_items(cart, currency):
    """Convierte los precios del carrito a la moneda seleccionada"""
    converted_items = []
    locale_map = {
        "COP": "es_CO",
        "USD": "en_US",
        "EUR": "es_ES",
        "MXN": "es_MX",
        "ARS": "es_AR",
    }
    locale = locale_map.get(currency, "es_CO")
    
    for item in cart:
        product = item['product']
        local_price = convert_currency_utils(product.price, "COP", currency)
        converted_items.append({
            'product': product,
            'quantity': item['quantity'],
            'converted_price': format_price(local_price, currency, locale),
            'converted_total': format_price(local_price * item['quantity'], currency, locale),
            'base_price': format_price(product.price, "COP", "es_CO"),
        })
    
    return converted_items

def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # inicia sesión automáticamente
            return redirect("product_list")  # o "home"
    else:
        form = UserCreationForm()
    return render(request, "registration/register.html", {"form": form})
    
class CustomLoginView(LoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        if self.request.user.is_staff:
            return reverse_lazy("admin_dashboard")
        return reverse_lazy("product_list") 

def custom_logout(request):
    logout(request)
    return redirect("product_list")

@login_required
def create_product(request):
    if not request.user.is_staff:  # solo admins o staff
        return redirect("product_list")

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("product_list")
    else:
        form = ProductForm()
    return render(request, "store/create_product.html", {"form": form})

def product_list(request):
    products = Product.objects.all()
    
    # Moneda válida: COP o USD, por defecto COP
    currency = request.session.get("currency", "COP")
    if currency not in ["COP", "USD"]:
        currency = "COP"
        request.session["currency"] = currency
    
    # Locales para formato
    locale = "es_CO" if currency == "COP" else "en_US"
    
    converted_products = []
    for p in products:
        # Conversión simple
        if currency == "COP":
            local_price = p.price
        else:  # USD
            local_price = convert_currency(p.price, "COP", "USD")
        
        converted_products.append({
            "obj": p,
            "converted_price": format_price(local_price, currency, locale),
            "currency": currency,
            "base_price": format_price(p.price, "COP", "es_CO"),
        })
    
    return render(request, "store/product_list.html", {
        "products": converted_products,
        "current_currency": currency
    })

def add_to_cart(request, pk):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=pk)
    cart.add(product)
    return redirect("cart_detail")

def cart_detail(request):
    cart = Cart(request)
    currency = request.session.get("currency", "COP")
    locale = "es_CO" if currency == "COP" else "en_US"
    
    cart_items = []
    total = 0
    
    for item in cart:
        product = item['product']
        quantity = item['quantity']
        
        # Precio convertido
        if currency == "COP":
            price = product.price
        else:
            price = convert_currency(product.price, "COP", "USD")
        
        item_total = price * quantity
        total += item_total
        
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'price': format_price(price, currency, locale),
            'total': format_price(item_total, currency, locale),
        })
    
    context = {
        'cart_items': cart_items,
        'total': format_price(total, currency, locale),
        'currency': currency,
    }
    return render(request, "store/cart_detail.html", context)

def checkout(request):
    cart = Cart(request)
    currency = request.session.get("currency", "COP")
    locale = "es_CO" if currency == "COP" else "en_US"
    
    # Calcular total (similar a cart_detail)
    total = 0
    for item in cart:
        product = item['product']
        if currency == "COP":
            price = product.price
        else:
            price = convert_currency(product.price, "COP", "USD")
        total += price * item['quantity']

    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        address = request.POST.get("address")

        # Crear pedido
        order = Order.objects.create(
            customer_name=name,
            customer_email=email,
            customer_address=address,
        )

        # Crear items del pedido
        for item in cart:
            OrderItem.objects.create(
                order=order,
                product=item["product"],
                quantity=item["quantity"],
                price=item["product"].price,
            )
            # Descontar stock
            product = item["product"]
            product.stock -= item["quantity"]
            product.save()

        cart.clear()
        return render(request, "store/checkout_done.html", {"order": order})

    context = {
        'cart': cart,
        'total': format_price(total, currency, locale),
        'currency': currency,
    }
    return render(request, "store/checkout.html", context)

