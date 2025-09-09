from django.http import JsonResponse
from django.shortcuts import render,redirect, get_object_or_404
from shop.form import CustomUserForm, FeedbackForm
from .models import *
from .models import Feedback
from django.contrib import messages
from django.contrib.auth import authenticate,login,logout
import  json

import logging
import uuid
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from django.contrib.auth.decorators import login_required

def home(request):
    products=Product.objects.filter(trending=1)
    return render(request, 'shop/index.html',{"products":products})

@login_required
def accounts(request):
    # Example: Fetch user info and orders
    user = request.user
    orders = Order.objects.filter(user=user).order_by('-id')
    return render(request, 'shop/accounts.html', {'user': user, 'orders': orders})

@login_required
def settings(request):
    user = request.user
    if request.method == 'POST':
        # Process form submission to update user info
        username = request.POST.get('username')
        email = request.POST.get('email')
        # Add more fields as needed
        user.username = username
        user.email = email
        user.save()
        messages.success(request, 'Settings updated successfully.')
        return redirect('settings')
    return render(request, 'shop/settings.html', {'user': user})

def about(request):
    return render(request, 'shop/about.html')

@login_required
def dashboard(request):
    user = request.user
    orders = Order.objects.filter(user=user).order_by('-id')
    if request.method == 'POST':
        # Process form submission to update user info (settings)
        username = request.POST.get('username')
        email = request.POST.get('email')
        user.username = username
        user.email = email
        user.save()
        messages.success(request, 'Settings updated successfully.')
        return redirect('dashboard')
    return render(request, 'shop/dashboard.html', {
        'user': user,
        'orders': orders,
    })

def favviewpage(request):
   if request.user.is_authenticated:
      fav=Favourite.objects.filter(user=request.user)
      return render(request,"shop/fav.html",{"fav":fav})
   else:
      return redirect("/")

def remove_fav(request,fid):
    try:
        item = get_object_or_404(Favourite, id=fid)
        item.delete()
        messages.success(request, "Item removed from favourites successfully.")
    except Exception as e:
        messages.error(request, f"Error removing item from favourites: {str(e)}")
    return redirect("/favviewpage")


def cart_page(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user)
        return render(request, "shop/cart.html", {"cart": cart})
    else:
        return redirect("/")
def remove_cart(request,cid):
    try:
        cartitem = get_object_or_404(Cart, id=cid)
        cartitem.delete()
        messages.success(request, "Item removed from cart successfully.")
    except Exception as e:
        messages.error(request, f"Error removing item from cart: {str(e)}")
    return redirect("/cart")

def checkout(request):
    logging.info(f"Checkout view called with method: {request.method}, user authenticated: {request.user.is_authenticated}")
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user)
        total_price = float(sum(item.total_cost for item in cart))
        logging.info(f"Cart items: {len(cart)}, total price: {total_price}")

        if request.method == 'POST':
            logging.info("Processing POST request for order")
            # Check if cart is empty
            if not cart:
                logging.warning("Cart is empty")
                return JsonResponse({'success': False, 'message': 'Your cart is empty.'})

            # Process the order
            fname = request.POST.get('fname')
            lname = request.POST.get('lname')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            logging.info(f"Form data - fname: {fname}, lname: {lname}, email: {email}, phone: {phone}")

            # Phone number validation: only digits and length 10
            if not phone.isdigit() or len(phone) != 10:
                logging.warning("Phone validation failed")
                return JsonResponse({'success': False, 'message': 'Phone number must be exactly 10 digits and contain only numbers.'})

            address = request.POST.get('address')
            city = request.POST.get('city')
            state = request.POST.get('state')
            country = request.POST.get('country')
            pincode = request.POST.get('pincode')
            payment_mode = request.POST.get('payment_mode')
            logging.info(f"Address data - address: {address}, city: {city}, payment_mode: {payment_mode}")

            try:
                logging.info("Starting order creation")
                # Create order
                order = Order.objects.create(
                    user=request.user,
                    fname=fname,
                    lname=lname,
                    email=email,
                    phone=phone,
                    address=address,
                    city=city,
                    state=state,
                    country=country,
                    pincode=pincode,
                    total_price=total_price,
                    payment_mode=payment_mode,
                    status='Pending'
                )
                logging.info(f"Order created with ID: {order.id}")

                # Generate tracking number
                order.tracking_no = f"ORD-{order.id}-{uuid.uuid4().hex[:8].upper()}"
                order.save()
                logging.info(f"Tracking number set: {order.tracking_no}")

                # Create order items
                for item in cart:
                    logging.info(f"Creating order item for product ID: {item.product.id}, qty: {item.product_qty}")
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        price=float(item.product.selling_price),
                        quantity=item.product_qty
                    )
                    logging.info(f"Order item created for product ID: {item.product.id}")

                    # Update product quantity
                    new_quantity = item.product.quantity - item.product_qty
                    if new_quantity < 0:
                        logging.error(f"Product {item.product.id} quantity cannot be negative. Current: {item.product.quantity}, requested: {item.product_qty}")
                        return JsonResponse({'success': False, 'message': 'Product stock not sufficient.'})
                    item.product.quantity = new_quantity
                    item.product.save()
                    logging.info(f"Product quantity updated for product ID: {item.product.id}, new qty: {new_quantity}")

                # Clear cart
                logging.info("Deleting cart items")
                cart.delete()
                logging.info("Cart cleared")

                # Redirect to order confirmation page
                redirect_url = f'/order-confirmation/{order.id}/'
                logging.info(f"Order successful, redirecting to: {redirect_url}")
                return JsonResponse({
                    'success': True,
                    'message': 'Order placed successfully!',
                    'order_id': order.id,
                    'tracking_no': order.tracking_no,
                    'redirect': redirect_url
                })
            except IntegrityError as e:
                logging.error(f"Database integrity error: {str(e)}", exc_info=True)
                return JsonResponse({'success': False, 'message': f'Database error: {str(e)}'})
            except ValidationError as e:
                logging.error(f"Validation error: {str(e)}", exc_info=True)
                return JsonResponse({'success': False, 'message': f'Validation error: {str(e)}'})
            except Exception as e:
                logging.error(f"Unexpected error placing order: {str(e)}", exc_info=True)
                return JsonResponse({'success': False, 'message': f'An unexpected error occurred: {str(e)}'})

        logging.info("Rendering checkout page")
        return render(request, "shop/checkout.html", {
            "cart": cart,
            "total_price": total_price
        })
    else:
        logging.warning("User not authenticated, cannot place order")
        return JsonResponse({'success': False, 'message': 'Please login to place an order.'})

def order_confirmation(request, order_id):
    if request.user.is_authenticated:
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            order_items = OrderItem.objects.filter(order=order)
            for item in order_items:
                item.total = item.price * item.quantity

            # Handle feedback form submission
            if request.method == 'POST':
                feedback_form = FeedbackForm(request.POST)
                if feedback_form.is_valid():
                    feedback = feedback_form.save(commit=False)
                    feedback.user = request.user
                    feedback.order = order
                    feedback.save()
                    messages.success(request, "Thank you for your feedback! Your input helps us improve our service.")
                    return redirect('order_confirmation', order_id=order_id)
                else:
                    messages.error(request, "Please correct the errors in the feedback form.")
            else:
                # Check if feedback already exists for this order
                try:
                    existing_feedback = Feedback.objects.get(order=order)
                    feedback_form = FeedbackForm(instance=existing_feedback)
                    feedback_submitted = True
                except Feedback.DoesNotExist:
                    feedback_form = FeedbackForm()
                    feedback_submitted = False

            return render(request, "shop/order_confirmation.html", {
                "order": order,
                "order_items": order_items,
                "feedback_form": feedback_form,
                "feedback_submitted": feedback_submitted
            })
        except Order.DoesNotExist:
            messages.error(request, "Order not found.")
            return redirect("/")
    else:
        return redirect("/login")

def fav_page(request):
   if request.headers.get('x-requested-with')=='XMLHttpRequest':
      if request.user.is_authenticated:
         try:
            data=json.loads(request.body)
            product_id=data['pid']
            if Product.objects.filter(id=product_id).exists():
               if Favourite.objects.filter(user=request.user, product_id=product_id).exists():
                  return JsonResponse({'status':'Product Already in Favourite'}, status=200)
               else:
                  try:
                     Favourite.objects.create(user=request.user, product_id=int(product_id))
                     return JsonResponse({'status':'Product Added to Favourite'}, status=200)
                  except Exception as e:
                     logging.error(f"Error adding to favourite: {str(e)}")
                     return JsonResponse({'status':'Error Adding to Favourite'}, status=500)
            else:
               return JsonResponse({'status':'Product Not Found'}, status=200)
         except json.JSONDecodeError:
            return JsonResponse({'status':'Invalid JSON'}, status=400)
         except KeyError:
            return JsonResponse({'status':'Missing Product ID'}, status=400)
      else:
         return JsonResponse({'status':'Login to Add Favourite'}, status=200)
   else:
      return JsonResponse({'status':'Invalid Access'}, status=200)



def add_to_cart(request):
   if request.headers.get('x-requested-with')=='XMLHttpRequest':
      if request.user.is_authenticated:
         try:
            data=json.loads(request.body)
            product_qty = int(data['product_qty'])
            product_id = int(data['pid'])
            if Product.objects.filter(id=product_id).exists():
               product_status=Product.objects.get(id=product_id)
               if Cart.objects.filter(user=request.user, product_id=product_id).exists():
                  cart_item = Cart.objects.get(user=request.user, product_id=product_id)
                  new_qty = cart_item.product_qty + product_qty
                  if product_status.quantity >= new_qty:
                     cart_item.product_qty = new_qty
                     cart_item.save()
                     return JsonResponse({'status':'Product Quantity Updated in Cart', 'redirect': '/cart'}, status=200)
                  else:
                     return JsonResponse({'status':'Product Stock Not Available'}, status=200)
               else:
                  if product_status.quantity>=product_qty:
                     Cart.objects.create(user=request.user, product=product_status, product_qty=product_qty)
                     return JsonResponse({'status':'product added to cart', 'redirect': '/cart'}, status=200)
                  else:
                     return JsonResponse({'status':'Product Stock Not Available'}, status=200)
            else:
               return JsonResponse({'status':'Product Not Found'}, status=200)
         except json.JSONDecodeError:
            return JsonResponse({'status':'Invalid JSON'}, status=400)
         except KeyError:
            return JsonResponse({'status':'Missing Product ID or Quantity'}, status=400)
         except ValueError:
            return JsonResponse({'status':'Invalid Product ID or Quantity'}, status=400)
         except Exception as e:
            return JsonResponse({'status':'Error: ' + str(e)}, status=500)
      else:
         return JsonResponse({'status':'Login to Add Cart'}, status=200)
   else:
      return JsonResponse({'status':'Invalid Access'}, status=200)


def update_cart(request, cid):
   if request.headers.get('x-requested-with')=='XMLHttpRequest':
      if request.user.is_authenticated:
         try:
            data=json.loads(request.body)
            product_qty=data['product_qty']
            if Cart.objects.filter(user=request.user, id=cid).exists():
               cart_item = Cart.objects.get(user=request.user, id=cid)
               if product_qty > 0 and product_qty <= cart_item.product.quantity:
                  cart_item.product_qty = product_qty
                  cart_item.save()
                  return JsonResponse({'status':'Cart Updated Successfully'}, status=200)
               else:
                  return JsonResponse({'status':'Invalid Quantity or Stock Not Available'}, status=200)
            else:
               return JsonResponse({'status':'Cart Item Not Found'}, status=200)
         except json.JSONDecodeError:
            return JsonResponse({'status':'Invalid JSON'}, status=400)
      else:
         return JsonResponse({'status':'Login to Update Cart'}, status=200)
   else:
      return JsonResponse({'status':'Invalid Access'}, status=200)


def buy_now(request):
   if request.method == 'POST':
      if request.user.is_authenticated:
         try:
            data=json.loads(request.body)
            product_qty=data['product_qty']
            product_id=data['pid']
            if Product.objects.filter(id=product_id).exists():
               product_status=Product.objects.get(id=product_id)
               if product_status.quantity >= product_qty:
                  # Clear existing cart and add this product
                  Cart.objects.filter(user=request.user).delete()
                  Cart.objects.create(user=request.user, product_id=product_id, product_qty=product_qty)
                  return JsonResponse({'status':'You Now Buy this Product', 'redirect': '/checkout'}, status=200)
               else:
                  return JsonResponse({'status':'Product Stock Not Available'}, status=200)
            else:
               return JsonResponse({'status':'Product Not Found'}, status=200)
         except json.JSONDecodeError:
            return JsonResponse({'status':'Invalid JSON'}, status=400)
      else:
         return JsonResponse({'status':'Login to Buy Now'}, status=200)
   else:
      return JsonResponse({'status':'Invalid Access'}, status=200)



def logout_page(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request,"Logged out Successfully")
    return redirect("/")


def login_page(request):
    if request.user.is_authenticated:
        return redirect("/")
    else:
     if request.method=='POST':
        name=request.POST.get('username')
        pwd=request.POST.get('password')
        user=authenticate(request,username=name,password=pwd)
        if user is not None:
            login(request,user)
            messages.success(request,"Login in Successfully")
            return redirect("/")
        else:
            messages.error(request, "Invalid User Name or Password")
            return redirect("/login")
    return render(request, 'shop/login.html')


def register(request):
    form=CustomUserForm()
    if request.method=='POST':
        form=CustomUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Registration Success you can Login Now...!")
            return redirect('/login')
    return render(request, 'shop/register.html',{'form':form})

def collections(request):
    category=Category.objects.filter(status=0)
    return render (request,'shop/collections.html',{"category":category})

def collectionsview(request,name):
    if(Category.objects.filter(name=name, status=0)):
        products=Product.objects.filter(category__name=name)
        return render (request,"shop/products/index.html",{"products":products,"category_name":name})
    else:
        messages.warning(request, "No such category Found")
        return redirect('collections')

def product_details(request,cname,pname):
    if(Category.objects.filter(name=cname, status=0)):
        if(Product.objects.filter(name=pname, status=0)):
         products=Product.objects.filter(name=pname, status=0).first()
         return render (request,"shop/products/product_details.html",{"products":products})
        else:
           messages.error(request, "No such Product  Found")
        return redirect('collections')
        
    else:
        messages.error(request, "No such Category Found")
        return redirect('collections')
