# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
import logging
import pytz
import datetime
import time
import hashlib
import os
import locale
import logging
import math

try:
    import json
except ImportError:
    import simplejson as json

from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404, render, redirect
from django.template import RequestContext, Template, Context
from django.template.loader import render_to_string
from django.views.generic import TemplateView, FormView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic.base import View
from django.conf import settings
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.mail import send_mail
from django.utils.decorators import method_decorator
from django.utils.timezone import now, localtime
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, logout as django_logout
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import logout, authenticate, login
from django.utils.translation import ugettext_lazy as _
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from openerplib import get_connection
from decimal import Decimal

import xmlrpclib

username = 'admin' #the user
pwd = 'admin'      #the password of the user
dbname = 'ecommerce_8'    #the database


# Get OpenERP Connection
connection = get_connection(hostname="localhost", database="ecommerce_8", login="admin", password="admin")

# Get logging interface
logger = logging.getLogger(__name__)

PPG = 25 # Products Per Page
PPR = 4  # Products Per Row


class BaseView(View):

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(BaseView, self).dispatch(*args, **kwargs)


class IndexView(BaseView):

    def get(self, request, *args, **kwargs):
        print 'request dict' , request.__dict__
        print 'query main' , request.POST.get('query', None)
#        if request.get(query):
#            query = ''

        cart_have_items = False
        page = 0
        if request.session.get('cart'):
            cart_have_items = True
        company_model = connection.get_model("res.company")
        company = company_model.search_read([],
                                             fields=['name', 'phone', 'email', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id'], order="name")

        category_obj = connection.get_model('product.public.category')
        category_ids = category_obj.search([])
        categs = category_obj.read(category_ids, ["name", 'parent_id'])

        product_model = connection.get_model("product.product")
#        if query:
#            products = product_model.search_read([('name', 'ilike', query), ('website_published','=', 'True')],
#                                                 fields=['name', 'list_price', 'image_medium', 'id',
#                                                         'seller_qty', 'uom_id', 'sale_delay', 'default_code',
#                                                         'warranty','description_sale'])
#        else:
#            products = product_model.search_read([('website_published','=', 'True')],
#                                                 fields=['name', 'list_price', 'image_medium', 'id',
#                                                         'seller_qty', 'uom_id', 'sale_delay', 'default_code',
#                                                         'warranty','description_sale'])

        products = product_model.search_read([('website_published','=', 'True') ],
                                             fields=['name', 'list_price', 'image_medium', 'id',
                                             'seller_qty', 'uom_id', 'sale_delay', 'default_code',
                                             'warranty', 'description_sale'], order="name")
#        print 'products', len(products)
        product_count = len(products)
        pager = self.pager(url="/ecommerce_sap/main", total=product_count, page=page, step=PPG, scope=30, url_args=None)
#        print 'pager', pager
        paginator = Paginator(products, 27)
        page = request.GET.get('page')
        try:
            prods = paginator.page(page)
        except PageNotAnInteger:
            prods = paginator.page(1)
        except EmptyPage:
            prods = paginator.page(paginator.num_pages)

        data = {
            'company_dict' : company[0],
            'categs' : categs,
            'page': pager,
            'products': prods,
            'items_open': [0, 3, 6, 9, 12, 15, 18, 21, 24],
            'cart_have_items': cart_have_items,
        }

        return render_to_response("index.html", data, context_instance=RequestContext(request))

    def pager(self, url, total, page=1, step=30, scope=5, url_args=None, context=None):
        # Compute Pager
        page_count = int(math.ceil(float(total) / step))


        page = max(1, min(int(page if str(page).isdigit() else 1), page_count))
        scope -= 1

        pmin = max(page - int(math.floor(scope/2)), 1)
        pmax = min(pmin + scope, page_count)
#        print 'page_count', page_count, total, step, page, pmax

        if pmax - pmin < scope:
            pmin = pmax - scope if pmax - scope > 0 else 1

        def get_url(page):
            _url = "%s/page/%s" % (url, page) if page > 1 else url
            if url_args:
                _url = "%s?%s" % (_url, werkzeug.url_encode(url_args))
#            print '_url', _url
            return _url

        return {
            "page_count": page_count,
            "offset": (page - 1) * step,
            "page": {
                'url': get_url(page),
                'num': page
            },
            "page_start": {
                'url': get_url(pmin),
                'num': pmin
            },
            "page_previous": {
                'url': get_url(max(pmin, page - 1)),
                'num': max(pmin, page - 1)
            },
            "page_next": {
                'url': get_url(min(pmax, page + 1)),
                'num': min(pmax, page + 1)
            },
            "page_end": {
                'url': get_url(pmax),
                'num': pmax
            },
            "pages": [
                {'url': get_url(page), 'num': page}
                for page in xrange(pmin, pmax+1)
            ]
        }


    def post(self, request, *args, **kwargs):
        page = 0
        product_model = connection.get_model("product.product")
        query = request.POST.get('search', None)

        company_model = connection.get_model("res.company")
        company = company_model.search_read([],
                                             fields=['name', 'phone', 'email', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id'], order="name")

        category_obj = connection.get_model('product.public.category')
        category_ids = category_obj.search([])
        categs = category_obj.read(category_ids, ["name", 'parent_id'])

        if query:
            products = product_model.search_read([('name', 'ilike', query), ('website_published','=', 'True')],
                                                 fields=['name', 'list_price', 'image_medium', 'id',
                                                         'seller_qty', 'uom_id', 'sale_delay', 'default_code',
                                                         'warranty','description_sale'])
        else:
            products = product_model.search_read([('website_published','=', 'True')],
                                                 fields=['name', 'list_price', 'image_medium', 'id',
                                                         'seller_qty', 'uom_id', 'sale_delay', 'default_code',
                                                         'warranty','description_sale'])
        product_count = len(products)
        pager = self.pager(url="/ecommerce_sap/main", total=product_count, page=page, step=PPG, scope=30, url_args=None)

        paginator = Paginator(products, 27)
        page = request.GET.get('page')
        try:
            prods = paginator.page(page)
        except PageNotAnInteger:
            prods = paginator.page(1)
        except EmptyPage:
            prods = paginator.page(paginator.num_pages)

        print 'query search', query

        data = {
            'company_dict' : company[0],
            'categs' : categs,
            'page': pager,
            'products': prods,
            'query': query,
            'items_open': [0, 3, 6, 9, 12, 15, 18, 21, 24],
        }

        return render_to_response("index.html", data, context_instance=RequestContext(request))


class ProductDetailView(BaseView):

    def get(self, request, *args, **kwargs):
        product_model = connection.get_model("product.product")
        logger.error('pk: {0}'.format(kwargs))
        product = product_model.search_read([('id', '=', kwargs['pk'])], [])

        company_model = connection.get_model("res.company")
        company = company_model.search_read([],
                                             fields=['name', 'phone', 'email', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id'], order="name")

        data = {
            'product': product[0],
            'company_dict' : company[0],

        }

        return render_to_response("product-detail.html", data, context_instance=RequestContext(request))


class CartBaseMixin(object):

    def _get_or_create_cart(self):
        created = False
        cart = self.request.session.get('cart', None)
        if not cart:
            cart = {
                'user': None,
                'total_without_taxes': Decimal(0.00),
                'taxes': Decimal(0.00),
                'total_with_taxes': Decimal(0.00),
                'items': []
            }

            created = True

        return (created, cart)

    def _remove_item_from_cart(self, item_id):
        """ Removes item from cart using item id """
        created, cart = self._get_or_create_cart()
        if not created:
            # Logic to remove element here
            cart_items = cart['items']
            logger.error(cart_items)
            for position, item in enumerate(cart_items):
                if item.has_key(item_id):
                    cart_items.pop(position)
                    logger.error("cart_items: {0}".format(cart_items))

        cart['items'] = cart_items
        self.request.session['cart'] = cart
        self._calculate_total_and_taxes()
        return cart

    def _calculate_total_and_taxes(self, tax=Decimal(0.16)):
        created, cart = self._get_or_create_cart()
        total = Decimal(0.00)
        total_without_taxes = Decimal(0.00)
        taxes = Decimal(0.00)

        if not created:
            cart_items = cart['items']
            for item in cart_items:
                total_without_taxes += item.values()[0]['total_item']

            taxes = total_without_taxes * tax
            total = total_without_taxes + taxes
            cart['total_without_taxes'] = total_without_taxes
            cart['taxes'] = total_without_taxes * tax
            cart['total_with_taxes'] = total
            self.request.session['cart'] = cart


class CartIndexView(CartBaseMixin, BaseView):

    def get(self, request, *args, **kwargs):
        created, cart = self._get_or_create_cart()
        if created:
            cart['user'] = request.user.id
            request.session['cart'] = cart

        company_model = connection.get_model("res.company")
        company = company_model.search_read([],
                                             fields=['name', 'phone', 'email', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id'], order="name")


        data = {
            'company_dict' : company[0],
            'cart_items': cart['items'],
            'cart_total': cart['total_with_taxes'],
            'cart_subtotal': cart['total_without_taxes'],
            'cart_iva': cart['taxes'],
            'user': request.user,
            'hook_url': request.session.get('hook_url'),
        }

        return render_to_response("cart_index.html", data, context_instance=RequestContext(request))


class CartAddorUpdateView(CartBaseMixin, BaseView):

    def post(self, request, *args, **kwargs):
        print request.POST.__dict__
        created, cart = self._get_or_create_cart()
        quantity = int(request.POST.get('quantity', 1)) if int(request.POST.get('quantity')) > 0 else 1
        print 'Quantity', int(request.POST.get('quantity', 1)), type(request.POST.get('quantity'))
        item = {
            'product_id': request.POST.get('product_id'),
            'product_name': request.POST.get('product_name'),
            'quantity': quantity,
            'unit_price': Decimal(request.POST.get('unit_price')),
            'uom': request.POST.get('uom'),
            'sale_delay': request.POST.get('sale_delay'),
            'product_code': request.POST.get('product_code'),
        }

        new = True
        # If cart exists we check if product exists in cart
        if cart['items']:
            for cart_item in cart['items']:
                if cart_item.has_key(item['product_id']):
                    if cart_item[item['product_id']]['quantity'] > item['quantity']:
                        logger.error(item['quantity'])
                        if item['quantity'] == 0:
                            logger.error('Trata de remover el item: {0}'.format(item['product_id']))
                            self._remove_item_from_cart(item['product_id'])
                        else:
                            remove = cart_item[item['product_id']]['quantity'] - item['quantity']
                            cart_item[item['product_id']]['quantity'] -= remove
                    else:
                        if item['quantity'] == cart_item[item['product_id']]['quantity']:
                            new_quantity = item['quantity']
                        else:
                            new_quantity = item['quantity'] - cart_item[item['product_id']]['quantity']
                        cart_item[item['product_id']]['quantity'] += new_quantity
                    cart_item[item['product_id']]['total_item'] = item['unit_price'] * cart_item[item['product_id']]['quantity']
                    new = False

            # If product not exists create a new one
            if new:
                cart['items'].append({item['product_id']: {
                    'name': item['product_name'],
                    'unit_price': item['unit_price'],
                    'quantity': item['quantity'],
                    'total_item': item['unit_price'] * item['quantity'],
                    'uom': item['uom'],
                    'sale_delay': item['sale_delay'],
                    'product_code': item['product_code'],
                }})

        else:
            # First element in cart
            cart['items'].append({item['product_id']: {
                'name': item['product_name'],
                'unit_price': item['unit_price'],
                'quantity': item['quantity'],
                'total_item': item['unit_price'] * item['quantity'],
                'uom': item['uom'],
                'sale_delay': item['sale_delay'],
                'product_code': item['product_code'],
            }})

        # Save cart to session in redis
        request.session['cart'] = cart
        self._calculate_total_and_taxes()

        return HttpResponseRedirect(reverse('cart-index'))


class DeleteItemFromCart(CartBaseMixin, View):

    def get(self, request, *args, **kwargs):
        product_model = connection.get_model("product.product")
        product = product_model.search_read([('id', '=', kwargs['pk'])], [])

        data = {
            'product': product[0],
            'product_id': kwargs['pk']
        }

        return render_to_response("confirm-delete.html", data, context_instance=RequestContext(request))

    def post(self, request, *args, **kwargs):
        self._remove_item_from_cart(request.POST.get('product_id'))
        return HttpResponseRedirect(reverse('cart-index'))


class CleanCartView(BaseView):

    def get(self, request, *args, **kwargs):
        if request.session.get('cart'):
            del request.session['cart']

        return redirect('index')
