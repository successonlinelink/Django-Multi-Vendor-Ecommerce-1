from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt # -> csrf_exempt is used to exempt the view from CSRF verification
from django.contrib import messages
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives, send_mail # for payment confirmation email

from decimal import Decimal
import requests
import stripe

from plugin.service_fee import calculate_service_fee
from plugin.tax_calculation import tax_calculation
from plugin.exchange_rate import convert_usd_to_kobo, convert_usd_to_ngn, get_usd_to_ngn_rate


from plugin.paginate_queryset import paginate_queryset
from store import models as store_models
from customer import models as customer_models
from vendor import models as vendor_models
from userauths import models as userauths_models

""" 
    All Payments use the same payment status for success and failure status are tunnelled in the same
    way, so you can use the same payment status for all payment methods.
"""
 
stripe.api_key = settings.STRIPE_SECRET_KEY

#! -> Clear Cart Items Functionality
def clear_cart_items(request):
    try:
        cart_id = request.session['cart_id'] # -> Get the cart_id from the session
        store_models.Cart.objects.filter(cart_id=cart_id).delete() # -> Delete all items in the cart with the given cart_id
    except:
        pass
    return

# 
def index(request):
    products = store_models.Product.objects.filter(status="Published")
    # categories = store_models.Category.objects.all()
    
    context = {
        "products": products,
        # "categories": categories,
    }
    return render(request, "store/index.html", context)


# Shop
def shop(request):
    products_list = store_models.Product.objects.filter(status="Published")
    categories = store_models.Category.objects.all()
    colors = store_models.VariantItem.objects.filter(variant__name='Color').values('title', 'content').distinct()
    sizes = store_models.VariantItem.objects.filter(variant__name='Size').values('title', 'content').distinct()
    item_display = [
        {"id": "1", "value": 1},
        {"id": "2", "value": 2},
        {"id": "3", "value": 3},
        {"id": "40", "value": 40},
        {"id": "50", "value": 50},
        {"id": "100", "value": 100},
    ]

    ratings = [
        {"id": "1", "value": "★☆☆☆☆"},
        {"id": "2", "value": "★★☆☆☆"},
        {"id": "3", "value": "★★★☆☆"},
        {"id": "4", "value": "★★★★☆"},
        {"id": "5", "value": "★★★★★"},
    ]

    prices = [
        {"id": "lowest", "value": "Highest to Lowest"},
        {"id": "highest", "value": "Lowest to Highest"},
    ]

    print(sizes)

    products = paginate_queryset(request, products_list, 10)

    context = {
        "products": products,
        "products_list": products_list,
        "categories": categories,
         'colors': colors,
        'sizes': sizes,
        'item_display': item_display,
        'ratings': ratings,
        'prices': prices,
    }
    return render(request, "store/shop.html", context)
###################


# Category
def category(request, id):
    category = store_models.Category.objects.get(id=id)
    products_list = store_models.Product.objects.filter(status="Published", category=category)

    query = request.GET.get("q")
    if query:
        products_list = products_list.filter(name__icontains=query)

    products = paginate_queryset(request, products_list, 10)

    context = {
        "products": products,
        "products_list": products_list,
        "category": category,
    }
    return render(request, "store/category.html", context)


# Vendors
def vendors(request):
    vendors = userauths_models.Profile.objects.filter(user_type="Vendor")
    
    context = {
        "vendors": vendors
    }
    return render(request, "store/vendors.html", context)
###########


#! Product Detail Page 
def product_detail(request, slug):
    product = store_models.Product.objects.get(status="Published", slug=slug)
    
    # This guy is responsible for the number of products you want to
    product_stock_range = range(1, product.stock + 1) # type: ignore

    related_products = store_models.Product.objects.filter(category=product.category).exclude(id=product.id) # type: ignore 
    #-> exclude(id=product.id) -> will not display the current product in view in the related products

    context = {
        "product": product,
        "product_stock_range": product_stock_range,
        "related_products": related_products,
    }
    return render(request, "store/product_detail.html", context)



#! Add to Cart
def add_to_cart(request):
    # Get parameters from the request (ID, color, size, quantity, cart_id) as defined in cart model
    id = request.GET.get("id")
    qty = request.GET.get("qty")
    color = request.GET.get("color")
    size = request.GET.get("size")
    cart_id = request.GET.get("cart_id")
    
    # assign the cart id to the session if it doesn't exist -> mind you, by default it doesn't exist, it will only exist once you assign it by selecting and adding an item in the cart
    request.session['cart_id'] = cart_id

    # Validate required fields
    if not id or not qty or not cart_id:
        return JsonResponse({"error": "No color or size selected"}, status=400) # bad request error

    # Try to fetch the product, return an error if it doesn't exist
    try:
        product = store_models.Product.objects.get(status="Published", id=id)
        
    except store_models.Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404) # page not found error

    # Check if the item is already in the cart
    existing_cart_item = store_models.Cart.objects.filter(cart_id=cart_id, product=product).first()

    # Check if quantity that user is adding exceed item stock qty
    if int(qty) > product.stock: # type: ignore
        return JsonResponse({"error": "Qty exceed current stock amount"}, status=404) # page not found error

    # If the item is not in the cart, create a new cart entry
    if not existing_cart_item:
        cart = store_models.Cart()
        cart.product = product
        cart.qty = qty
        cart.price = product.price
        cart.color = color
        cart.size = size
        cart.sub_total = Decimal(product.price) * Decimal(qty) 
        cart.shipping = Decimal(product.shipping) * Decimal(qty) 
        cart.total = cart.sub_total + cart.shipping
        cart.user = request.user if request.user.is_authenticated else None
        cart.cart_id = cart_id
        cart.save()

        message = "Item added to cart"  
    else:
        # If the item exists in the cart, update the existing entry
        existing_cart_item.color = color
        existing_cart_item.size = size
        existing_cart_item.qty = qty
        existing_cart_item.price = product.price
        existing_cart_item.sub_total = Decimal(product.price) * Decimal(qty) 
        existing_cart_item.shipping = Decimal(product.shipping) * Decimal(qty) 
        existing_cart_item.total = existing_cart_item.sub_total +  existing_cart_item.shipping
        existing_cart_item.user = request.user if request.user.is_authenticated else None
        existing_cart_item.cart_id = cart_id
        existing_cart_item.save()

        message = "Cart updated"

    # Count the total number of items in the cart
    total_cart_items = store_models.Cart.objects.filter(cart_id=cart_id)
    cart_sub_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(sub_total = models.Sum("sub_total"))['sub_total'] # type: ignore

    # Return the response with the cart update message and total cart items
    return JsonResponse({
        "message": message ,
        "total_cart_items": total_cart_items.count(),
        "cart_sub_total": "{:,.2f}".format(cart_sub_total), # {:,.2f} -> creates comas(,) and decimal points(.) to amounts
        "item_sub_total": "{:,.2f}".format(existing_cart_item.sub_total) if existing_cart_item else "{:,.2f}".format(cart.sub_total) 
    })


#! Cart
def cart(request): # -> this guy is responsible for displaying the items in the cart
    if "cart_id" in request.session: # -> check if the cart_id exists in the session
        cart_id = request.session['cart_id'] # -> if it exists, assign it to the cart_id variable
    else:
        cart_id = None

    items = store_models.Cart.objects.filter(cart_id=cart_id) # Retrieve all items in the cart for the current session
    cart_sub_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(sub_total = models.Sum("sub_total"))['sub_total']
    # this guy will get the sub_total of the items in the cart  
    
    try: # -> try to get the addresses of the user
        addresses = customer_models.Address.objects.filter(user=request.user)
    except:
        addresses = None

    if not items: # -> if there are no items in the cart, redirect to the index page with a warning message
        messages.warning(request, "No item in cart")
        return redirect("store:index")

    context = {
        "items": items,
        "cart_sub_total": cart_sub_total,
        "addresses": addresses,
    }
    return render(request, "store/cart.html", context)


#! Delete Cart Functionality
def delete_cart_item(request):
    # get the parameters from the request to be deleted
    id = request.GET.get("id")
    item_id = request.GET.get("item_id")
    cart_id = request.GET.get("cart_id")
    
    # Validate required fields
    if not id and not item_id and not cart_id:
        return JsonResponse({"error": "Item or Product id not found"}, status=400)

    try: # -> Try to fetch the product using the ID
        product = store_models.Product.objects.get(status="Published", id=id)
    except store_models.Product.DoesNotExist: # -> If the product does not exist, return an error
        return JsonResponse({"error": "Product not found"}, status=404)

    # Check if the item is already in the cart
    item = store_models.Cart.objects.get(product=product, id=item_id)
    item.delete() # -> Delete the item from the cart if it exists

    # Count the total number of items in the cart
    total_cart_items = store_models.Cart.objects.filter(cart_id=cart_id)
    cart_sub_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(sub_total = models.Sum("sub_total"))['sub_total']

    return JsonResponse({
        "message": "Item deleted",
        "total_cart_items": total_cart_items.count(),
        "cart_sub_total": "{:,.2f}".format(cart_sub_total) if cart_sub_total else 0.00
    })


# The order does not have a file rather you populate it in the check out page
# -> The order is created when you click on the create order button in the cart page (proceed to checkout)
#! Create Order Functionality
def create_order(request):
    if request.method == "POST": # -> Check if the request method is POST
        address_id = request.POST.get("address")
        
        if not address_id: # -> If no address is selected, redirect to the cart page with a warning message
            messages.warning(request, "Please select an address to continue")
            return redirect("store:cart")
        
        # -> Get the address for the user - the one already saved in the database - will display under the cart page - you just have to select it 
        address = customer_models.Address.objects.filter(user=request.user, id=address_id).first()

        if "cart_id" in request.session: # -> Check if the cart_id exists in the session
            cart_id = request.session['cart_id'] # -> if it exists, assign it to the cart_id variable
        else:
            cart_id = None # -> if it doesn't exist, set cart_id to None

        # Retrieve all items in the cart for the current session
        items = store_models.Cart.objects.filter(cart_id=cart_id) # Retrieve all items in the cart for the current session
        
        # this guy will get the sub_total of the items in the cart if there is
        cart_sub_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(sub_total = models.Sum("sub_total"))['sub_total'] 

        # this guy will get the shipping total of the items in the cart if there is
        cart_shipping_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(shipping = models.Sum("shipping"))['shipping']
        

        order = store_models.Order() # -> Create a new order instance - more like getting it ready to put something
        order.sub_total = cart_sub_total # -> Set the sub_total of the order to the cart sub_total
        order.customer = request.user # -> Set the customer of the order to the current user
        order.address = address # -> Set the address of the order to the selected address
        order.shipping = cart_shipping_total # -> Set the shipping total of the order to the cart shipping total
        order.tax = tax_calculation(address.country, cart_sub_total) # type: ignore # -> Calculate the tax based on the address country and cart sub_total
        order.total = order.sub_total + order.shipping + Decimal(order.tax) # -> Set the total of the order to the sum of sub_total, shipping, and tax
        order.service_fee = calculate_service_fee(order.total) # -> Calculate the service fee based on the order total
        order.total += order.service_fee # -> Add the service fee to the total of the order
        order.initial_total = order.total
        order.save()


        for i in items: # -> Loop through each item in the cart
            store_models.OrderItem.objects.create( # -> Create a new order item for each item in the cart
                order=order,
                product=i.product,
                qty=i.qty,
                color=i.color,
                size=i.size,
                price=i.price,
                sub_total=i.sub_total,
                shipping=i.shipping,
                tax=tax_calculation(address.country, i.sub_total), # type: ignore
                total=i.total,
                initial_total=i.total,
                vendor=i.product.vendor
            )

            order.vendors.add(i.product.vendor) # -> Add the vendor of the product to the order vendors
            #* Note: The order.vendors is a ManyToManyField in the Order model, so you can add multiple vendors to the order if there are multiple products from different vendors in the cart which is just the logic above it -> order.vendors.add(i.product.vendor)
    
    return redirect("store:checkout", order.order_id)
    # You can only be redirected to the checkout page if you make an order and -> order.order_id - means order with its ID


#! Coupon Functionality
def coupon_apply(request, order_id):
    
    try: 
        order = store_models.Order.objects.get(order_id=order_id) # -> Get the order with the given order_id
        order_items = store_models.OrderItem.objects.filter(order=order) # -> Get all order items associated with the order
        
    except store_models.Order.DoesNotExist: # -> If the order does not exist, return an error message
        messages.error(request, "Order not found")
        return redirect("store:cart")

    if request.method == 'POST': # -> Check if the request method is POST
        coupon_code = request.POST.get("coupon_code")
        
        if not coupon_code: # -> If no coupon code is entered, return an error message
            messages.error(request, "No coupon entered")
            return redirect("store:checkout", order.order_id)
            
        try: # -> Try to fetch the coupon using the code
            coupon = store_models.Coupon.objects.get(code=coupon_code) # -> Get the coupon with the given code
            
        except store_models.Coupon.DoesNotExist: # -> If the coupon does not exist, return an error message
            messages.error(request, "Coupon does not exist")
            return redirect("store:checkout", order.order_id)
        
        if coupon in order.coupons.all(): # -> Check if the coupon is already applied to the order
            messages.warning(request, "Coupon already activated")
            return redirect("store:checkout", order.order_id)
        
        
        else: # -> If the coupon is not already applied, proceed to apply it
            total_discount = 0 # -> Initialize total discount to 0
            
            # Note: If a vendor gives you a coupon and you select two items from different vendors, the coupon will only apply to the items from the vendor that issued the coupon to you not with the other vendors items
            for item in order_items: # -> Loop through each order item
                # -> Check if the coupon is applicable to the item and not already applied, if its already applied, it will not apply again, it will throw the error of (Coupon does not exist) as done above,  
                if coupon.vendor == item.product.vendor and coupon not in item.coupon.all(): 
                    item_discount = item.total * coupon.discount / 100  # Discount for this item
                    total_discount += item_discount # -> Add the item discount to the total discount

                    item.coupon.add(coupon) # -> Add the coupon to the item
                    item.total -= item_discount # -> Subtract the item discount from the item total
                    item.saved += item_discount # -> Add the item discount to the item saved amount
                    item.save() # -> Save the item with the updated totals

            # Apply total discount to the order after processing all items
            if total_discount > 0: # -> If there is a total discount, apply it to the order
                order.coupons.add(coupon) # -> Add the coupon to the order
                order.total -= total_discount # -> Subtract the total discount from the order total
                order.sub_total -= total_discount # -> Subtract the total discount from the order sub_total
                order.saved += total_discount # -> Add the total discount to the order saved amount
                order.save() # -> Save the order with the updated totals
        
        messages.success(request, "Coupon Activated")
        return redirect("store:checkout", order.order_id)


#! Checkout Functionality - The Checkout payments functionalities and contexts should come after writing each of the payments method except -> order = store_models.Order.objects.get(order_id=order_id)
def checkout(request, order_id):
    # This guy will come first then after writing payment methods you start passing them in the conext
    order = store_models.Order.objects.get(order_id=order_id) # -> Get the order with the given order_id
    
    amount_in_kobo = convert_usd_to_kobo(order.total)
    amount_in_ngn = convert_usd_to_ngn(order.total)

    context = {
        "order": order,
        "amount_in_kobo":amount_in_kobo,
        "amount_in_ngn":round(amount_in_ngn, 2),
        
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
        "paypal_client_id": settings.PAYPAL_CLIENT_ID, # coming from paypal configuration
        "paystack_public_key":settings.PAYSTACK_PUBLIC_KEY,
        "flutterwave_public_key":settings.FLUTTERWAVE_PUBLIC_KEY,
    }

    return render(request, "store/checkout.html", context)


#! Stripe Payment Functionality
# -> This is the function that will handle the stripe payment
@csrf_exempt
def stripe_payment(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id) # -> Get the order with the given order_id
    stripe.api_key = settings.STRIPE_SECRET_KEY # -> Set the Stripe secret key from settings

    checkout_session = stripe.checkout.Session.create( # -> Create a new checkout session with Stripe
        customer_email = order.address.email,
        payment_method_types=['card'],
        line_items = [
            {
                'price_data': {
                    'currency': 'USD',
                    'product_data': {
                        'name': order.address.full_name
                    },
                    'unit_amount': int(order.total * 100) # -> Convert the total amount to cents (Stripe requires amounts in cents)
                },
                'quantity': 1 # -> Set the quantity to 1 since we are charging for the entire order
            }
        ],
        mode = 'payment',
        success_url = request.build_absolute_uri(reverse("store:stripe_payment_verify", args=[order.order_id])) + "?session_id={CHECKOUT_SESSION_ID}" + "&payment_method=Stripe", # -> Redirect to this URL on successful payment with the session ID and payment method
        cancel_url = request.build_absolute_uri(reverse("store:stripe_payment_verify", args=[order.order_id])) # -> Redirect to this URL on payment cancellation with the session ID and order ID
    )

    # print("checkkout session", checkout_session)
    return JsonResponse({"sessionId": checkout_session.id}) # checkout_session -> has been given to (sessionId) and will be redirected accoording to the payment status


#! Stripe Payment Verification Functionality
def stripe_payment_verify(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id) # -> Get the order with the given order_id

    session_id = request.GET.get("session_id") # -> Get the session ID from the request
    session = stripe.checkout.Session.retrieve(session_id) # -> Retrieve the checkout session from Stripe using the session ID

    if session.payment_status == "paid": # -> Check if the payment status of the session is "paid"
        if order.payment_status == "Processing": # -> but you have to Check if the order payment status is "Processing"
            order.payment_status = "Paid" # but if its successfull
            order.save() # save it

            # -> Clear the cart items after successful payment
            clear_cart_items(request)
            
            # Email Configuration
            # #  -> Prepare the data to be used in the email template for the customer
            # customer_merge_data = { 
            #     'order': order,
            #     'order_items': order.order_items(),
            # }
            
            # # Send Order Emails to Customer
            # subject = f"New Order!"
            # text_body = render_to_string("email/order/customer/customer_new_order.txt", customer_merge_data)
            # html_body = render_to_string("email/order/customer/customer_new_order.html", customer_merge_data)

            # # -> Create a new email message
            # msg = EmailMultiAlternatives( 
            #     subject=subject, from_email=settings.FROM_EMAIL,
            #     to=[order.address.email], body=text_body
            # )
            
            # msg.attach_alternative(html_body, "text/html") # -> Attach the HTML alternative to the email message
            # # -> Send the email message to the customer
            # msg.send()
            
            # # Create a notification of purchase order for the user - that's after placing the order
            customer_models.Notifications.objects.create(type="New Order", user=request.user) 
            # -> Create a new notification for the user


            # Send Order Emails to Vendors - the items that have been purchased by the customer
            # -> Loop through each item in the order and send an email to the vendor 
            for item in order.order_items():
                
            #     vendor_merge_data = {
            #         'item': item,
            #     }
                
            #     subject = f"New Sale!"
            #     text_body = render_to_string("email/order/vendor/vendor_new_order.txt", vendor_merge_data)
            #     html_body = render_to_string("email/order/vendor/vendor_new_order.html", vendor_merge_data)

            #     msg = EmailMultiAlternatives(
            #         subject=subject, from_email=settings.FROM_EMAIL,
            #         to=[item.vendor.email], body=text_body
            #         # Note: items is the variable name of the loop
            #     )
                
            #     msg.attach_alternative(html_body, "text/html") # -> Attach the HTML alternative to the email message
            #     # -> Send the email message to the Vendor
            #     msg.send()
            
            #     # Create a notification of sale order for the vendor - that's after customer place an order
                vendor_models.Notifications.objects.create(type="New Sale", user=item.vendor, order=item) 
            #     # -> Create a new notification for the user
            #     # Note: The order is passed to the notification so that the vendor can see the order details in the notification

            return redirect(f"/payment_status/{order.order_id}/?payment_status=paid") # -> Redirect to the payment status page with the order ID and payment status as "paid"
    
    return redirect(f"/payment_status/{order.order_id}/?payment_status=failed") # # -> If the payment status is not "paid", redirect to the payment status page with the order ID and payment status as "failed"
    
    
    
#! Paypal Configuration
# Get the access first
def get_paypal_access_token():
    token_url = 'https://api.sandbox.paypal.com/v1/oauth2/token' # Use the sandbox URL for testing
    data = {'grant_type': 'client_credentials'} # grant_type is client_credentials for PayPal API
    auth = (settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET_ID) # Use your PayPal client ID and secret ID from settings
    response = requests.post(token_url, data=data, auth=auth) # Make a POST request to get the access token

    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f'Failed to get access token from PayPal. Status code: {response.status_code}') 

#! PayPal Payment Functionality
def paypal_payment_verify(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id) # Get the order with the given order_id

    transaction_id = request.GET.get("transaction_id") # Get the transaction ID from the request
    paypal_api_url = f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{transaction_id}' # Use the sandbox URL for testing
    headers = { # Set the headers for the request
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {get_paypal_access_token()}',
    }
    response = requests.get(paypal_api_url, headers=headers)

    if response.status_code == 200: # Check if the response status code is 200 (OK)
        paypal_order_data = response.json() # Parse the JSON response to get the order data
        paypal_payment_status = paypal_order_data['status'] # Get the payment status from the order data
        if paypal_payment_status == 'COMPLETED': # -> Check if the payment status is COMPLETED
            if order.payment_status == "Processing": # -> Check if the order payment status is Processing
                order.payment_status = "Paid" # -> Update the order payment status to Paid
                payment_method = request.GET.get("payment_method") # Get the payment method from the request (url)
                order.payment_method = payment_method # -> Set the payment method for the order
                order.save()
                clear_cart_items(request) # Clear the cart items after successful payment
                return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
    else:
        return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")


# Paystack Integration
def paystack_payment_verify(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id) # Get the order with the given order_id
    reference = request.GET.get('reference', '') 
    # Get the reference from the request, which is used to verify the payment - if reference is not appended return an empty string

    if reference: # Check if the reference is provided in the request
        headers = { # Set the headers for the request to Paystack API
            "Authorization": f"Bearer {settings.PAYSTACK_PRIVATE_KEY}",
            "Content-Type": "application/json"
        }

        # Verify the transaction
        response = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
        response_data = response.json()

        # Check if the response is successful
        if response_data['status']:
            if response_data['data']['status'] == 'success':
                if order.payment_status == "Processing":
                    order.payment_status = "Paid"
                    payment_method = request.GET.get("payment_method")
                    order.payment_method = payment_method
                    order.save()
                    
                    clear_cart_items(request)
                    
                    return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
                else:
                    return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
            else:
                # Payment failed
                return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
        else:
            return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
    else:
        return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")


#! Flutterwave Integration
def flutterwave_payment_callback(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)

    payment_id = request.GET.get('tx_ref')
    status = request.GET.get('status')

    headers = {
        'Authorization': f'Bearer {settings.FLUTTERWAVE_PRIVATE_KEY}'
    }
    response = requests.get(f'https://api.flutterwave.com/v3/charges/verify_by_id/{payment_id}', headers=headers)

    if response.status_code == 200:
        if order.payment_status == "Processing":
            order.payment_status = "Paid"
            payment_method = request.GET.get("payment_method")
            order.payment_method = payment_method
            order.save()
            clear_cart_items(request)
            return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
        else:
            return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
    else:
        return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")


# Payment Status Functionality
def payment_status(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id) # Get the order with the given order_id
    payment_status = request.GET.get("payment_status") # Get the payment status from the request -> from the search url

    context = {
        "order": order,
        "payment_status": payment_status
    }
    return render(request, "store/payment_status.html", context)

# Filter Products
def filter_products(request):
    products = store_models.Product.objects.all()

    # Get filters from the AJAX request
    categories = request.GET.getlist('categories[]')
    rating = request.GET.getlist('rating[]')
    sizes = request.GET.getlist('sizes[]')
    colors = request.GET.getlist('colors[]')
    price_order = request.GET.get('prices')
    search_filter = request.GET.get('searchFilter')
    display = request.GET.get('display')

    # print("categories =======", categories)
    # print("rating =======", rating)
    # print("sizes =======", sizes)
    # print("colors =======", colors)
    # print("price_order =======", price_order)
    # print("search_filter =======", search_filter)
    # print("display =======", display)

   
    # Apply category filtering
    if categories:
        products = products.filter(category__id__in=categories)

    # Apply rating filtering
    if rating:
        products = products.filter(reviews__rating__in=rating).distinct()

    

    # Apply size filtering
    if sizes:
        products = products.filter(variant__variant_items__content__in=sizes).distinct()

    # Apply color filtering
    if colors:
        products = products.filter(variant__variant_items__content__in=colors).distinct()

    # Apply price ordering
    if price_order == 'lowest':
        products = products.order_by('-price')
    elif price_order == 'highest':
        products = products.order_by('price')

    # Apply search filter
    if search_filter:
        products = products.filter(name__icontains=search_filter)

    if display:
        products = products.filter()[:int(display)]


    # Render the filtered products as HTML using render_to_string
    html = render_to_string('partials/_store.html', {'products': products})

    return JsonResponse({'html': html, 'product_count': products.count()})


# Tracking Order
def order_tracker_page(request):
    if request.method == "POST":
        item_id = request.POST.get("item_id")
        return redirect("store:order_tracker_detail", item_id)
    
    return render(request, "store/order_tracker_page.html")

# Tracking Order Page
def order_tracker_detail(request, item_id):
    try:
        item = store_models.OrderItem.objects.filter(models.Q(item_id=item_id) | models.Q(tracking_id=item_id)).first()
    except:
        item = None
        messages.error(request, "Order not found!")
        return redirect("store:order_tracker_page")
    
    context = {
        "item": item,
    }
    return render(request, "store/order_tracker.html", context)
##############


# def about(request):
#     return render(request, "pages/about.html")

# def contact(request):
#     if request.method == "POST":
#         full_name = request.POST.get("full_name")
#         email = request.POST.get("email")
#         subject = request.POST.get("subject")
#         message = request.POST.get("message")

#         userauths_models.ContactMessage.objects.create(
#             full_name=full_name,
#             email=email,
#             subject=subject,
#             message=message,
#         )
#         messages.success(request, "Message sent successfully")
#         return redirect("store:contact")
#     return render(request, "pages/contact.html")

# def faqs(request):
#     return render(request, "pages/faqs.html")

# def privacy_policy(request):
#     return render(request, "pages/privacy_policy.html")

# def terms_conditions(request):
#     return render(request, "pages/terms_conditions.html")