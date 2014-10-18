from django.conf.urls import patterns, include, url
from django.contrib import admin
from core.views import (IndexView, ProductDetailView, CartIndexView, 
						CartAddorUpdateView, DeleteItemFromCart, CleanCartView)

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', IndexView.as_view(), name="index"),
    url(r'^product-detail/(?P<pk>\d+)/$', ProductDetailView.as_view(), name='product-detail'),
    url(r'^admin/', include(admin.site.urls)),
    url(r"", include('lot.urls')),
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}, name="login"),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}, name="logout"),
    url(r'^cart/index/$', CartIndexView.as_view(), name="cart-index"),
    url(r'^cart/add/$', CartAddorUpdateView.as_view(), name="cart-add"),
    url(r'^delete-from-cart/(?P<pk>\d+)/$', DeleteItemFromCart.as_view(), name="delete-from-cart"),
    url(r'^cart/clean/$', CleanCartView.as_view(), name="clean-cart"),
)
