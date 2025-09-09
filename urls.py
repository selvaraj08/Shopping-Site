from django.urls import path
from . import views


urlpatterns =[
    path('',views.home,name="home"),
    path('register/',views.register,name="register"),
    path('login',views.login_page,name="login"),
    path('logout',views.logout_page,name="logout"),
    path('cart',views.cart_page,name="cart_page"),
    path('fav',views.fav_page,name="fav"),
    path('favviewpage',views.favviewpage,name="favviewpage"),
    path('remove_fav/<str:fid>',views.remove_fav,name="remove_fav"),
    path('remove_cart/<str:cid>',views.remove_cart,name="remove_cart"),
    path('checkout', views.checkout, name="checkout"),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name="order_confirmation"),
    path('collections',views.collections,name="collections"),
    path('collections/<str:name>',views.collectionsview,name="collectionsview"),
    path('collections/<str:cname>/<str:pname>',views.product_details,name="product_details"),
    path('addtocart',views.add_to_cart,name="add_to_cart"),
    path('update_cart/<str:cid>/', views.update_cart, name='update_cart'),
    path('buynow', views.buy_now, name='buy_now'),
    path('accounts/', views.accounts, name='accounts'),
    path('settings/', views.settings, name='settings'),
    path('about/', views.about, name='about'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
