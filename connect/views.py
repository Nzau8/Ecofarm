from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Count, F, Q, Sum, Min, Max, Avg
from django.db.models.functions import ExtractMonth
from django.utils import timezone
from datetime import timedelta
import json
from .models import (
    User, Product, Order, OrderItem, Cart, CartItem, Negotiation, Review, 
    Discussion, Comment, Course, Resource, LearningProgress, Story, Event, 
    EventRegistration, Message, Report, ProductImage, Post, PostComment, PostImage, 
    FriendRequest, ProductVariant, BulkDiscount, ProductTag, Notification, Conversation,
    DiscussionImage, CourseModule, CourseContent
)
from .forms import (
    UserSignUpForm, ProductForm, OrderForm, NegotiationForm, ReviewForm, 
    ContactForm, DiscussionForm, CommentForm, StoryForm, EventForm, MessageForm, 
    ReportForm, ResourceForm, PostForm, PostImageForm, PostCommentForm,
    ProductVariantForm, BulkDiscountForm, ProductTagForm, EditProfileForm,
    CourseForm, CourseModuleForm, CourseContentForm
)
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.cache import cache
from django.db.models import Q, Count
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.conf import settings
from django.views.decorators.cache import cache_page
from haversine import haversine, Unit
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .mpesa import process_split_payment

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)

def get_filtered_products(request):
    products = Product.objects.filter(is_available=True)
    
    # Basic filters
    category = request.GET.get('category')
    search = request.GET.get('search')
    sort = request.GET.get('sort')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    rating = request.GET.get('rating')
    tags = request.GET.getlist('tags')
    in_stock = request.GET.get('in_stock')
    
    # Apply filters
    if category:
        products = products.filter(category=category)
    
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(tags__name__icontains=search)
        ).distinct()
    
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except (ValueError, TypeError):
            pass
    
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except (ValueError, TypeError):
            pass
    
    if rating:
        try:
            products = products.filter(average_rating__gte=float(rating))
        except (ValueError, TypeError):
            pass
    
    if tags:
        products = products.filter(tags__name__in=tags)
    
    if in_stock == 'true':
        products = products.filter(quantity__gt=0)
    
    # Sorting
    if sort == 'price_low':
        products = products.order_by('price')
    elif sort == 'price_high':
        products = products.order_by('-price')
    elif sort == 'rating':
        products = products.order_by('-average_rating')
    elif sort == 'popularity':
        products = products.order_by('-views_count')
    else:
        products = products.order_by('-created_at')
    
    # Optimize queries
    products = products.select_related('seller').prefetch_related('images', 'tags')
    
    return products

def marketplace(request):
    products = get_filtered_products(request)
    recently_viewed = None
    
    if request.user.is_authenticated:
        # Get recently viewed products from session
        recently_viewed_ids = request.session.get('recently_viewed', [])
        if recently_viewed_ids:
            recently_viewed = Product.objects.filter(
                id__in=recently_viewed_ids
            ).select_related('seller').prefetch_related('images')[:5]
    
    # Get all available tags for filtering
    tags = ProductTag.objects.annotate(
        product_count=Count('products')
    ).filter(product_count__gt=0)
    
    # Price range for filtering
    price_range = Product.objects.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    
    # Paginate products
    paginator = Paginator(products, 12)  # Show 12 products per page
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    context = {
        'products': products,
        'categories': Product.Category.choices,
        'tags': tags,
        'price_range': price_range,
        'recently_viewed': recently_viewed,
    }
    
    response = render(request, 'marketplace.html', context)
    return response

def home(request):
    featured_products = Product.objects.filter(is_available=True).order_by('-created_at')[:6]
    recent_reviews = Review.objects.select_related('buyer', 'product').order_by('-created_at')[:5]
    return render(request, 'home.html', {
        'featured_products': featured_products,
        'recent_reviews': recent_reviews,
    })

def about(request):
    recent_reviews = Review.objects.select_related('buyer', 'product').order_by('-created_at')[:5]
    recent_negotiations = Negotiation.objects.select_related('buyer', 'seller', 'product').order_by('-created_at')[:5]
    return render(request, 'about.html', {
        'recent_reviews': recent_reviews,
        'recent_negotiations': recent_negotiations,
    })

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Here you would typically send an email with the form data
            # For now, we'll just show a success message
            messages.success(request, 'Your message has been sent successfully! We will get back to you soon.')
            return redirect('contact')
    else:
        form = ContactForm()
    
    return render(request, 'contact.html', {'form': form})

def signup(request):
    if request.method == 'POST':
        form = UserSignUpForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            # Check if current user is admin and wants to make new user admin
            if request.user.is_authenticated and request.user.role == 'admin' and request.POST.get('make_admin'):
                user.role = 'admin'
            user.save()
            messages.success(request, 'Account created successfully! You can now log in.')
            return redirect('login')
    else:
        form = UserSignUpForm()
    return render(request, 'signup.html', {'form': form})

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('user_profile', username=request.user.username)
    else:
        form = EditProfileForm(instance=request.user)
    return render(request, 'edit_profile.html', {'form': form})

@login_required
def update_profile_picture(request):
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        request.user.profile_picture = request.FILES['profile_picture']
        request.user.save()
        messages.success(request, 'Profile picture updated successfully!')
    return redirect('profile', username=request.user.username)

@login_required
def update_cover_photo(request):
    if request.method == 'POST' and request.FILES.get('cover_photo'):
        request.user.cover_photo = request.FILES['cover_photo']
        request.user.save()
        messages.success(request, 'Cover photo updated successfully!')
    return redirect('profile', username=request.user.username)

# Marketplace Views
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    reviews = Review.objects.filter(product=product).select_related('buyer').order_by('-created_at')
    if request.user.is_authenticated:
        user_review = reviews.filter(buyer=request.user).first()
    else:
        user_review = None
    
    if request.method == 'POST' and request.user.is_authenticated:
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.buyer = request.user
            review.product = product
            review.save()
            # Update product rating stats
            product.update_rating_stats()
            messages.success(request, 'Review added successfully!')
            return redirect('product_detail', pk=pk)
    else:
        review_form = ReviewForm()
    
    # Track product view
    if request.user.is_authenticated and request.user != product.seller:
        product.increment_views()
    
    context = {
        'product': product,
        'reviews': reviews,
        'user_review': user_review,
        'review_form': review_form,
    }
    
    return render(request, 'product_detail.html', context)

@login_required
def cart(request):
    cart, created = Cart.objects.get_or_create(buyer=request.user)
    
    # Calculate totals for each item and overall
    cart_items = cart.items.all()
    for item in cart_items:
        item.total = item.product.price * item.quantity
        
        # Get available riders in the same operating zone as the seller
        if item.product.seller.location:
            item.available_riders = User.objects.filter(
                role=User.Role.BODA_RIDER,
                is_active=True,
                operating_zone=item.product.seller.operating_zone
            ).annotate(
                completed_deliveries=Count('delivery_orders', filter=Q(delivery_orders__status='completed'))
            ).order_by('-completed_deliveries')[:5]
        else:
            item.available_riders = []
    
    subtotal = sum(item.total for item in cart_items)
    delivery_fee = 200  # Base delivery fee
    total = subtotal + delivery_fee
    
    context = {
        'cart': cart,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'total': total,
    }
    
    return render(request, 'cart.html', context)

@login_required
def select_rider(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        rider_id = request.POST.get('rider_id')
        
        cart_item = get_object_or_404(CartItem, id=item_id, cart__buyer=request.user)
        rider = get_object_or_404(User, id=rider_id, role=User.Role.BODA_RIDER)
        
        # Store the selected rider in the session
        if 'selected_riders' not in request.session:
            request.session['selected_riders'] = {}
        request.session['selected_riders'][str(item_id)] = rider_id
        request.session.modified = True
        
        # Calculate delivery fee based on zone
        delivery_fee = calculate_delivery_fee(cart_item.product.seller, rider)
        
        # Get completed deliveries count
        completed_deliveries = Order.objects.filter(
            boda_rider=rider,
            status='completed'
        ).count()
        
        return JsonResponse({
            'status': 'success',
            'delivery_fee': delivery_fee,
            'rider': {
                'id': rider.id,
                'name': rider.get_full_name() or rider.username,
                'completed_deliveries': completed_deliveries,
                'zone': rider.operating_zone
            }
        })
    
    return JsonResponse({'status': 'error'}, status=400)

def calculate_delivery_fee(seller, rider):
    """Calculate delivery fee based on haversine distance between seller and rider"""
    base_fee = 200  # Base delivery fee in KES
    
    # If either seller or rider doesn't have coordinates, fall back to zone-based pricing
    if not all([seller.latitude, seller.longitude, rider.latitude, rider.longitude]):
        return base_fee + (100 if seller.operating_zone != rider.operating_zone else 0)
    
    # Calculate distance using haversine formula
    seller_coords = (float(seller.latitude), float(seller.longitude))
    rider_coords = (float(rider.latitude), float(rider.longitude))
    distance_km = haversine(seller_coords, rider_coords, unit=Unit.KILOMETERS)
    
    # Calculate fee based on distance
    # Base fee for first 5 km, then 50 KES per additional km
    if distance_km <= 5:
        return base_fee
    else:
        additional_km = distance_km - 5
        additional_fee = additional_km * 50  # 50 KES per additional km
        return base_fee + int(additional_fee)

@csrf_exempt
def mpesa_callback(request):
    """Handle STK push callback"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            result = data.get('Body', {}).get('stkCallback', {})
            
            if result.get('ResultCode') == 0:
                # Payment successful
                merchant_request_id = result.get('MerchantRequestID')
                # Update order status and process split payments
                order = Order.objects.get(mpesa_request_id=merchant_request_id)
                order.payment_status = 'paid'
                order.save()
                
                # Process split payments
                success, message = process_split_payment(order)
                if success:
                    return JsonResponse({'status': 'success'})
                else:
                    return JsonResponse({'status': 'error', 'message': message})
            else:
                return JsonResponse({'status': 'error', 'message': 'Payment failed'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def mpesa_b2c_timeout(request):
    """Handle B2C timeout"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Log timeout for monitoring
            print(f"B2C Timeout: {data}")
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def mpesa_b2c_result(request):
    """Handle B2C result"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            result = data.get('Result', {})
            
            if result.get('ResultCode') == 0:
                # Payment successful
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'B2C payment failed'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, buyer=request.user)
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.buyer = request.user
            
            # Get the first item's seller
            first_item = cart.items.first()
            if first_item:
                order.seller = first_item.product.seller
            
            # Get selected rider if boda delivery
            if order.delivery_type == 'boda':
                selected_riders = request.session.get('selected_riders', {})
                first_item_id = str(first_item.id)
                if first_item_id in selected_riders:
                    rider_id = selected_riders[first_item_id]
                    order.boda_rider = User.objects.get(id=rider_id)
            
            # Calculate total amount including delivery fee
            subtotal = sum(item.product.price * item.quantity for item in cart.items.all())
            if order.delivery_type == 'boda' and order.boda_rider:
                delivery_fee = calculate_delivery_fee(order.seller, order.boda_rider)
            else:
                delivery_fee = 0
            
            order.total_amount = subtotal + delivery_fee
            order.save()
            
            # Add cart items to order
            order.cart_items.add(*cart.items.all())
            
            # Create order items
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price_at_time=cart_item.product.price,
                    subtotal=cart_item.product.price * cart_item.quantity
                )
            
            # Process M-Pesa payment
            try:
                success, message = process_split_payment(order)
                if success:
                    # Clear cart and session data
                    cart.items.all().delete()
                    if 'selected_riders' in request.session:
                        del request.session['selected_riders']
                    
                    messages.success(request, 'Order placed successfully! Check your phone for M-Pesa prompt.')
                    return redirect('order_confirmation', pk=order.pk)
                else:
                    messages.error(request, f'Payment failed: {message}')
                    return redirect('checkout')
            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')
                return redirect('checkout')
    else:
        form = OrderForm()
    
    return render(request, 'checkout.html', {
        'form': form,
        'cart': cart,
    })

@login_required
def order_confirmation(request, pk):
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    return render(request, 'order_confirmation.html', {'order': order})

@login_required
def wishlist(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        if product in request.user.wishlist.all():
            request.user.wishlist.remove(product)
            messages.success(request, 'Product removed from wishlist!')
        else:
            request.user.wishlist.add(product)
            messages.success(request, 'Product added to wishlist!')
        return redirect('wishlist')
    
    return render(request, 'wishlist.html')

# Dashboard Views
@login_required
def seller_dashboard(request):
    if not request.user.is_seller():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    products = Product.objects.filter(seller=request.user)
    recent_orders = Order.objects.filter(items__product__seller=request.user).distinct().order_by('-created_at')[:5]
    
    return render(request, 'seller_dashboard.html', {
        'products': products,
        'recent_orders': recent_orders,
    })

@login_required
def buyer_dashboard(request):
    if not request.user.is_buyer():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    recent_orders = Order.objects.filter(buyer=request.user).order_by('-created_at')[:5]
    wishlist_items = request.user.wishlist.all()
    
    return render(request, 'buyer_dashboard.html', {
        'recent_orders': recent_orders,
        'wishlist_items': wishlist_items,
    })

@login_required
def boda_dashboard(request):
    if not request.user.is_boda_rider():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    active_deliveries = Order.objects.filter(boda_rider=request.user, status='shipped')
    completed_deliveries = Order.objects.filter(boda_rider=request.user, status='delivered').order_by('-updated_at')[:10]
    
    return render(request, 'boda_dashboard.html', {
        'active_deliveries': active_deliveries,
        'completed_deliveries': completed_deliveries,
    })

def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Get statistics
    user_roles = {
        'buyers': User.objects.filter(role='buyer').count(),
        'sellers': User.objects.filter(role='seller').count(),
        'boda_riders': User.objects.filter(role='boda_rider').count(),
    }
    
    # Get course statistics
    total_courses = Course.objects.count()
    published_courses = Course.objects.filter(is_published=True).count()
    total_enrollments = LearningProgress.objects.count()
    recent_courses = Course.objects.select_related('instructor').order_by('-created_at')[:5]
    
    context = {
        'total_users': User.objects.count(),
        'total_products': Product.objects.count(),
        'total_orders': Order.objects.count(),
        'reported_issues': Report.objects.filter(resolved=False).count(),
        'user_roles': user_roles,
        'recent_users': User.objects.order_by('-date_joined')[:5],
        'recent_orders': Order.objects.order_by('-created_at')[:5],
        'recent_reports': Report.objects.filter(resolved=False).order_by('-created_at')[:5],
        'sales_data': [0] * 12,  # Placeholder for monthly sales data
        
        # Course statistics
        'total_courses': total_courses,
        'published_courses': published_courses,
        'total_enrollments': total_enrollments,
        'recent_courses': recent_courses,
    }
    
    return render(request, 'admin_dashboard.html', context)

@login_required
def add_product(request):
    if not request.user.is_seller():
        messages.error(request, 'You do not have permission to add products.')
        return redirect('home')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()  # Save the product first
            form.save_m2m()  # Now save many-to-many relationships
            
            # Handle product images
            images = request.FILES.getlist('images')
            for i, image in enumerate(images):
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_primary=(i == 0)  # First image is primary
                )
            
            messages.success(request, 'Product added successfully!')
            return redirect('seller_dashboard')
    else:
        form = ProductForm()
    
    return render(request, 'add_product.html', {'form': form})

@login_required
def edit_product(request, pk):
    if not request.user.is_seller():
        messages.error(request, 'You do not have permission to edit products.')
        return redirect('home')
    
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            
            # Handle product images
            images = request.FILES.getlist('images')
            if images:
                # Delete existing images if new ones are uploaded
                product.images.all().delete()
                for i, image in enumerate(images):
                    ProductImage.objects.create(
                        product=product,
                        image=image,
                        is_primary=(i == 0)  # First image is primary
                    )
            
            messages.success(request, 'Product updated successfully!')
            return redirect('seller_dashboard')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'edit_product.html', {'form': form, 'product': product})

@login_required
def track_product_view(request, pk):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        product.increment_views()
        
        # Add to recently viewed in session
        recently_viewed = request.session.get('recently_viewed', [])
        if pk in recently_viewed:
            recently_viewed.remove(pk)
        recently_viewed.insert(0, pk)
        request.session['recently_viewed'] = recently_viewed[:5]
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def product_variants(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    
    if request.method == 'POST':
        form = ProductVariantForm(request.POST)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = product
            variant.save()
            return JsonResponse({
                'status': 'success',
                'variant': {
                    'id': variant.id,
                    'name': str(variant),
                    'price': float(variant.price),
                    'stock': variant.stock
                }
            })
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    
    variants = product.variants.all()
    return JsonResponse({
        'status': 'success',
        'variants': list(variants.values('id', 'size', 'weight', 'price', 'stock', 'sku'))
    })

@login_required
def delete_variant(request, pk):
    variant = get_object_or_404(ProductVariant, pk=pk)
    if request.user != variant.product.seller:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        variant.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def delete_review(request, pk):
    review = get_object_or_404(Review, pk=pk, buyer=request.user)
    if request.method == 'POST':
        product = review.product
        review.delete()
        product.update_rating_stats()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def create_bulk_discount(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    
    if request.method == 'POST':
        form = BulkDiscountForm(request.POST)
        if form.is_valid():
            discount = form.save(commit=False)
            discount.product = product
            discount.save()
            return JsonResponse({
                'status': 'success',
                'discount': {
                    'id': discount.id,
                    'min_quantity': discount.min_quantity,
                    'discount_percentage': float(discount.discount_percentage)
                }
            })
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def delete_bulk_discount(request, pk):
    discount = get_object_or_404(BulkDiscount, pk=pk)
    if request.user != discount.product.seller:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        discount.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def manage_tags(request):
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        form = ProductTagForm(request.POST)
        if form.is_valid():
            tag = form.save()
            return JsonResponse({
                'status': 'success',
                'tag': {
                    'id': tag.id,
                    'name': tag.name,
                    'slug': tag.slug
                }
            })
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    
    tags = ProductTag.objects.annotate(product_count=Count('products'))
    return JsonResponse({
        'status': 'success',
        'tags': list(tags.values('id', 'name', 'slug', 'product_count'))
    })

@login_required
def delete_tag(request, pk):
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    tag = get_object_or_404(ProductTag, pk=pk)
    if request.method == 'POST':
        tag.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def farmer_stories(request):
    stories = Story.objects.all().order_by('-created_at')
    return render(request, 'farmer_stories.html', {'stories': stories})

# Learning Hub Views
def learning_hub(request):
    courses = Course.objects.filter(is_published=True).order_by('-created_at')[:6]
    resources = Resource.objects.order_by('-created_at')[:8]
    
    learning_progress = None
    if request.user.is_authenticated:
        learning_progress = LearningProgress.objects.filter(user=request.user).order_by('-last_accessed')
    
    return render(request, 'learning_hub.html', {
        'courses': courses,
        'resources': resources,
        'learning_progress': learning_progress,
    })

def course_details(request, pk):
    course = get_object_or_404(Course, pk=pk, is_published=True)
    modules = course.modules.all().prefetch_related('contents')
    
    learning_progress = None
    if request.user.is_authenticated:
        learning_progress, created = LearningProgress.objects.get_or_create(
            user=request.user,
            course=course
        )
    
    return render(request, 'course_details.html', {
        'course': course,
        'modules': modules,
        'learning_progress': learning_progress,
    })

@login_required
def learning_progress(request):
    progress = LearningProgress.objects.filter(user=request.user).order_by('-last_accessed')
    return render(request, 'learning_progress.html', {'progress': progress})

def resources_list(request):
    resources = Resource.objects.order_by('-created_at')
    return render(request, 'resources_list.html', {'resources': resources})

def resource_details(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    return render(request, 'resource_details.html', {'resource': resource})

@login_required
def create_resource(request):
    if not request.user.is_staff:
        return redirect('learning_hub')
        
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('resources_list')
    else:
        form = ResourceForm()
    
    return render(request, 'create_resource.html', {'form': form})

# Community Views
def community_home(request):
    discussions = Discussion.objects.select_related('author').annotate(
        comments_count=Count('comments'),
        views_count=F('views')
    ).order_by('-created_at')
    
    # Handle category filtering
    category = request.GET.get('category')
    if category:
        discussions = discussions.filter(category=category)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(discussions, 10)  # Show 10 discussions per page
    try:
        discussions = paginator.page(page)
    except PageNotAnInteger:
        discussions = paginator.page(1)
    except EmptyPage:
        discussions = paginator.page(paginator.num_pages)
    
    return render(request, 'community_home.html', {
        'discussions': discussions,
        'current_category': category,
    })

@login_required
def community(request):
    discussions = Discussion.objects.all().order_by('-created_at')
    featured_topics = Discussion.objects.filter(is_featured=True)[:3]
    expert_tips = Discussion.objects.filter(is_expert_tip=True)[:3]
    farmer_stories = Story.objects.all().order_by('-created_at')[:3]
    upcoming_events = Event.objects.filter(start_date__gte=timezone.now()).order_by('start_date')[:3]
    
    context = {
        'discussions': discussions,
        'featured_topics': featured_topics,
        'expert_tips': expert_tips,
        'farmer_stories': farmer_stories,
        'upcoming_events': upcoming_events,
    }
    return render(request, 'community.html', context)

@login_required
def discussion_details(request, pk):
    discussion = get_object_or_404(Discussion, pk=pk)
    comments = discussion.comments.all().order_by('-created_at')
    related_discussions = Discussion.objects.filter(
        Q(category=discussion.category) | Q(tags__icontains=discussion.tags)
    ).exclude(pk=discussion.pk)[:3]
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.discussion = discussion
            comment.author = request.user
            comment.save()
            messages.success(request, 'Your comment has been added.')
            return redirect('discussion_details', pk=pk)
    else:
        form = CommentForm()
    
    context = {
        'discussion': discussion,
        'comments': comments,
        'form': form,
        'related_discussions': related_discussions,
    }
    return render(request, 'discussion_details.html', context)

@login_required
def create_discussion(request):
    if request.method == 'POST':
        form = DiscussionForm(request.POST, request.FILES)
        if form.is_valid():
            discussion = form.save(commit=False)
            discussion.author = request.user
            discussion.save()
            
            # Handle multiple images
            images = request.FILES.getlist('images')
            for image in images:
                DiscussionImage.objects.create(image=image, discussion=discussion)
            
            messages.success(request, 'Your discussion has been created.')
            return redirect('discussion_details', pk=discussion.pk)
    else:
        form = DiscussionForm()
    
    return render(request, 'create_discussion.html', {'form': form})

@login_required
def edit_discussion(request, pk):
    discussion = get_object_or_404(Discussion, pk=pk, author=request.user)
    if request.method == 'POST':
        form = DiscussionForm(request.POST, instance=discussion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your discussion has been updated.')
            return redirect('discussion_details', pk=pk)
    else:
        form = DiscussionForm(instance=discussion)
    
    return render(request, 'edit_discussion.html', {'form': form, 'discussion': discussion})

@login_required
def delete_discussion(request, pk):
    discussion = get_object_or_404(Discussion, pk=pk, author=request.user)
    if request.method == 'POST':
        discussion.delete()
        messages.success(request, 'Your discussion has been deleted.')
        return redirect('community')
    return render(request, 'delete_discussion.html', {'discussion': discussion})

@login_required
def farmer_stories(request):
    stories = Story.objects.all().order_by('-created_at')
    return render(request, 'farmer_stories.html', {'stories': stories})

@login_required
def create_story(request):
    if request.method == 'POST':
        form = StoryForm(request.POST, request.FILES)
        if form.is_valid():
            story = form.save(commit=False)
            story.author = request.user
            story.save()
            messages.success(request, 'Your story has been published.')
            return redirect('farmer_stories')
    else:
        form = StoryForm()
    
    return render(request, 'create_story.html', {'form': form})

@login_required
def events(request):
    upcoming_events = Event.objects.filter(start_date__gte=timezone.now()).order_by('start_date')
    past_events = Event.objects.filter(end_date__lt=timezone.now()).order_by('-end_date')
    return render(request, 'events.html', {
        'upcoming_events': upcoming_events,
        'past_events': past_events,
    })

@login_required
def event_details(request, pk):
    event = get_object_or_404(Event, pk=pk)
    is_registered = EventRegistration.objects.filter(event=event, user=request.user).exists()
    
    if request.method == 'POST':
        if not is_registered and event.can_register():
            EventRegistration.objects.create(event=event, user=request.user)
            messages.success(request, 'You have successfully registered for this event.')
        return redirect('event_details', pk=pk)
    
    context = {
        'event': event,
        'is_registered': is_registered,
        'participants': event.participants.all(),
    }
    return render(request, 'event_details.html', context)

@login_required
def messages_list(request):
    received_messages = Message.objects.filter(recipient=request.user).order_by('-created_at')
    sent_messages = Message.objects.filter(sender=request.user).order_by('-created_at')
    return render(request, 'messages.html', {
        'received_messages': received_messages,
        'sent_messages': sent_messages,
    })

@login_required
def message_seller(request):
    if request.method == 'POST':
        print(f"[DEBUG] Message seller request received from user: {request.user.username}")
        content = request.POST.get('content')
        seller_id = request.POST.get('seller_id')
        
        print(f"[DEBUG] Seller ID: {seller_id}, Content: {content}")
        
        try:
            seller = get_object_or_404(User, id=seller_id, role=User.Role.SELLER)
            print(f"[DEBUG] Found seller: {seller.username}")
            
            # Find or create conversation
            conversation = Conversation.objects.filter(
                participants=request.user
            ).filter(
                participants=seller
            ).filter(order__isnull=True).first()
            
            if not conversation:
                print("[DEBUG] Creating new conversation")
                conversation = Conversation.objects.create()
                conversation.participants.add(request.user, seller)
                conversation.save()
            
            if content:
                message = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=content,
                    is_read=False
                )
                print(f"[DEBUG] Message created successfully with ID: {message.id}")
                
                # Create notification for seller
                Notification.objects.create(
                    user=seller,
                    message=f"New message from {request.user.get_full_name() or request.user.username}"
                )
                
                return JsonResponse({
                    'status': 'success',
                    'message': {
                        'id': message.id,
                        'content': message.content,
                        'sender': message.sender.username,
                        'created_at': message.created_at.strftime('%b %d, %Y, %I:%M %p')
                    }
                })
            else:
                print("[DEBUG] Error: Empty message content")
                return JsonResponse({'status': 'error', 'message': 'Message content cannot be empty'}, status=400)
        except Exception as e:
            print(f"[DEBUG] Error creating message: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def report_content(request, content_type, content_id):
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.content_type = content_type
            report.content_id = content_id
            report.save()
            messages.success(request, 'Your report has been submitted.')
            return redirect('community')
    else:
        form = ReportForm()
    
    return render(request, 'report_content.html', {'form': form})

@login_required
def community_rules(request):
    return render(request, 'community_rules.html')

# Delivery Views
@login_required
def delivery_tracking(request, pk):
    order = get_object_or_404(Order, pk=pk)
    
    # Check if user has permission to view this order
    if not (request.user == order.buyer or request.user == order.boda_rider or request.user == order.items.first().product.seller):
        messages.error(request, 'You do not have permission to view this order.')
        return redirect('home')
    
    return render(request, 'order_tracking.html', {
        'order': order,
    })

@login_required
def confirm_delivery(request, pk):
    order = get_object_or_404(Order, pk=pk)
    
    # Check if user is the buyer
    if request.user != order.buyer:
        messages.error(request, 'You do not have permission to confirm this delivery.')
        return redirect('home')
    
    if request.method == 'POST':
        order.status = 'delivered'
        order.save()
        messages.success(request, 'Delivery confirmed successfully!')
        return redirect('order_tracking', pk=pk)
    
    return render(request, 'confirm_delivery.html', {
        'order': order,
    })

# Utility Views
@login_required
def notifications(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'notifications.html', {'notifications': notifications})

@login_required
def mark_notification_read(request, notification_id):
    if request.method == 'POST':
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return redirect('notifications')

def search_results(request):
    query = request.GET.get('q', '')
    if query:
        # Search across multiple models using Q objects
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct()

        resources = Resource.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )

        discussions = Discussion.objects.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query)
        )
    else:
        products = Product.objects.none()
        resources = Resource.objects.none()
        discussions = Discussion.objects.none()

    context = {
        'query': query,
        'products': products[:10],
        'resources': resources[:10],
        'discussions': discussions[:10],
    }
    return render(request, 'search_results.html', context)

# API Views
@login_required
def add_to_cart(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        variant_id = request.POST.get('variant_id')
        
        try:
            product = get_object_or_404(Product, id=product_id)
            
            # Validate quantity against product constraints
            if quantity < product.min_order_quantity:
                messages.error(request, f'Minimum order quantity is {product.min_order_quantity} {product.unit}')
                return redirect('product_detail', pk=product_id)
            
            if product.max_order_quantity and quantity > product.max_order_quantity:
                messages.error(request, f'Maximum order quantity is {product.max_order_quantity} {product.unit}')
                return redirect('product_detail', pk=product_id)
            
            if quantity > product.quantity:
                messages.error(request, f'Only {product.quantity} {product.unit} available')
                return redirect('product_detail', pk=product_id)

            # If variant is specified, validate it
            variant = None
            if variant_id:
                variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
                if quantity > variant.stock:
                    messages.error(request, f'Only {variant.stock} {product.unit} available for this variant')
                    return redirect('product_detail', pk=product_id)
            
            cart, created = Cart.objects.get_or_create(buyer=request.user)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                variant=variant,
                defaults={'quantity': quantity}
            )
            
            if not created:
                new_quantity = cart_item.quantity + quantity
                if new_quantity > product.quantity:
                    messages.error(request, 'Cannot add more. Total quantity would exceed available stock.')
                    return redirect('cart')
                cart_item.quantity = new_quantity
                cart_item.save()
            
            messages.success(request, 'Product added to cart successfully')
            return redirect('cart')
            
        except ValueError:
            messages.error(request, 'Invalid quantity')
            return redirect('cart')
            
    messages.error(request, 'Invalid request')
    return redirect('cart')

@login_required
def remove_from_cart(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        cart = get_object_or_404(Cart, buyer=request.user)
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()
        messages.success(request, 'Product removed from cart successfully')
        return redirect('cart')
    messages.error(request, 'Invalid request')
    return redirect('cart')

@login_required
def add_to_wishlist(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        
        if product not in request.user.wishlist.all():
            request.user.wishlist.add(product)
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def remove_from_wishlist(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        
        if product in request.user.wishlist.all():
            request.user.wishlist.remove(product)
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def create_negotiation(request):
    if request.method == 'POST':
        form = NegotiationForm(request.POST)
        if form.is_valid():
            negotiation = form.save(commit=False)
            negotiation.buyer = request.user
            negotiation.save()
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def respond_to_negotiation(request, pk):
    negotiation = get_object_or_404(Negotiation, pk=pk)
    if request.user == negotiation.seller:
        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'accept':
                negotiation.status = Negotiation.Status.ACCEPTED
            elif action == 'reject':
                negotiation.status = Negotiation.Status.REJECTED
            negotiation.save()
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def resolve_report(request, pk):
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        report = get_object_or_404(Report, pk=pk)
        report.resolved = True
        report.resolved_at = timezone.now()
        report.resolved_by = request.user
        report.save()
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            
            if 'image' in request.FILES:
                PostImage.objects.create(
                    post=post,
                    image=request.FILES['image'],
                    caption=request.POST.get('caption', '')
                )
            
            return redirect('news_feed')
    else:
        form = PostForm()
    
    return render(request, 'social/create_post.html', {
        'post_form': form
    })

@login_required
def add_image_to_post(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    if request.method == 'POST' and 'image' in request.FILES:
        PostImage.objects.create(
            post=post,
            image=request.FILES['image'],
            caption=request.POST.get('caption', '')
        )
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def like_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
    
    return JsonResponse({
        'status': 'success',
        'liked': liked,
        'count': post.get_like_count()
    })

@login_required
def add_post_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        data = json.loads(request.body)
        comment = PostComment.objects.create(
            post=post,
            author=request.user,
            content=data['content']
        )
        
        return JsonResponse({
            'status': 'success',
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'author': {
                    'name': comment.author.get_full_name(),
                    'profile_picture': comment.author.profile_picture.url if comment.author.profile_picture else None
                },
                'created_at': comment.created_at.strftime('%b %d, %Y %H:%M')
            }
        })
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def reply_to_comment(request, pk):
    parent_comment = get_object_or_404(PostComment, pk=pk)
    if request.method == 'POST':
        data = json.loads(request.body)
        reply = PostComment.objects.create(
            post=parent_comment.post,
            author=request.user,
            content=data['content'],
            parent_comment=parent_comment
        )
        
        return JsonResponse({
            'status': 'success',
            'comment': {
                'id': reply.id,
                'content': reply.content,
                'author': {
                    'name': reply.author.get_full_name(),
                    'profile_picture': reply.author.profile_picture.url if reply.author.profile_picture else None
                },
                'created_at': reply.created_at.strftime('%b %d, %Y %H:%M')
            }
        })
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def share_post(request, pk):
    original_post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        post = Post.objects.create(
            author=request.user,
            content=request.POST.get('content', ''),
            shared_post=original_post,
            privacy=request.POST.get('privacy', 'public')
        )
        return redirect('post_detail', pk=post.pk)
    
    return redirect('news_feed')

@login_required
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user == post.author:
        post.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=403)

@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    return render(request, 'social/post_detail.html', {
        'post': post,
        'comment_form': PostCommentForm()
    })

@login_required
def news_feed(request):
    # Get posts from friends and followed users
    following_ids = request.user.following.values_list('id', flat=True)
    friend_ids = request.user.friends.values_list('id', flat=True)
    visible_users = list(set(list(following_ids) + list(friend_ids) + [request.user.id]))
    
    posts = Post.objects.filter(
        Q(author_id__in=visible_users) | 
        Q(privacy='public')
    ).select_related('author').prefetch_related('likes', 'post_images', 'post_comments').order_by('-created_at')
    
    suggested_users = User.objects.exclude(
        id__in=list(following_ids) + list(friend_ids) + [request.user.id]
    )[:5]
    
    upcoming_events = Event.objects.filter(
        end_date__gte=timezone.now()
    ).order_by('start_date')[:3]
    
    return render(request, 'social/news_feed.html', {
        'posts': posts,
        'post_form': PostForm(),
        'image_form': PostImageForm(),
        'suggested_users': suggested_users,
        'upcoming_events': upcoming_events
    })

@login_required
def user_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(
        Q(author=profile_user, privacy='public') |
        Q(author=profile_user, privacy='friends', author__friends=request.user) |
        Q(author=profile_user) & Q(author=request.user)  # Fixed the repeated keyword argument
    ).select_related('author').prefetch_related('likes', 'post_images', 'post_comments').order_by('-created_at')
    
    is_friend = request.user.friends.filter(id=profile_user.id).exists()
    is_following = request.user.following.filter(id=profile_user.id).exists()
    
    context = {
        'profile_user': profile_user,
        'posts': posts,
        'is_friend': is_friend,
        'is_following': is_following,
        'post_form': PostForm() if request.user == profile_user else None,
        'image_form': PostImageForm() if request.user == profile_user else None,
    }
    return render(request, 'social/user_profile.html', context)

@login_required
def friend_list(request):
    friends = request.user.friends.all()
    following = request.user.following.all()
    followers = request.user.followers.all()
    
    context = {
        'friends': friends,
        'following': following,
        'followers': followers,
    }
    return render(request, 'social/friend_list.html', context)

@login_required
def send_friend_request(request, user_id):
    to_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        # Don't allow sending request to yourself
        if request.user == to_user:
            return JsonResponse({'status': 'error', 'message': 'Cannot send friend request to yourself'}, status=400)
        
        # Don't allow sending request if already friends
        if request.user.friends.filter(id=user_id).exists():
            return JsonResponse({'status': 'error', 'message': 'Already friends'}, status=400)
        
        # Don't allow sending request if one already exists
        if FriendRequest.objects.filter(from_user=request.user, to_user=to_user).exists():
            return JsonResponse({'status': 'error', 'message': 'Friend request already sent'}, status=400)
        
        FriendRequest.objects.create(from_user=request.user, to_user=to_user)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def accept_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    if request.method == 'POST':
        # Add each user to the other's friends list
        request.user.friends.add(friend_request.from_user)
        
        # Delete the friend request
        friend_request.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def reject_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    if request.method == 'POST':
        friend_request.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def follow_user(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        # Don't allow following yourself
        if request.user == user_to_follow:
            return JsonResponse({'status': 'error', 'message': 'Cannot follow yourself'}, status=400)
        
        # Add to following
        request.user.following.add(user_to_follow)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def unfollow_user(request, user_id):
    user_to_unfollow = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        # Remove from following
        request.user.following.remove(user_to_unfollow)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

class CustomLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        if self.request.user.is_seller():
            return reverse_lazy('seller_dashboard')
        elif self.request.user.is_buyer():
            return reverse_lazy('buyer_dashboard')
        elif self.request.user.is_boda_rider():
            return reverse_lazy('boda_dashboard')
        elif self.request.user.is_staff:
            return reverse_lazy('admin_dashboard')
        return reverse_lazy('home')

login = CustomLoginView.as_view()

def quick_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product_quick_view.html', {'product': product})

@login_required
def story_details(request, pk):
    story = get_object_or_404(Story, pk=pk)
    return render(request, 'story_details.html', {'story': story})

@login_required
def edit_story(request, pk):
    story = get_object_or_404(Story, pk=pk, author=request.user)
    if request.method == 'POST':
        form = StoryForm(request.POST, request.FILES, instance=story)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your story has been updated.')
            return redirect('story_details', pk=story.pk)
    else:
        form = StoryForm(instance=story)
    return render(request, 'edit_story.html', {'form': form, 'story': story})

@login_required
def like_story(request, pk):
    story = get_object_or_404(Story, pk=pk)
    if request.user in story.likes.all():
        story.likes.remove(request.user)
    else:
        story.likes.add(request.user)
    return redirect('story_details', pk=pk)

@login_required
def comment_story(request, pk):
    story = get_object_or_404(Story, pk=pk)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            StoryComment.objects.create(
                story=story,
                author=request.user,
                content=content
            )
            messages.success(request, 'Your comment has been posted.')
    return redirect('story_details', pk=pk)

@login_required
def story_details(request, pk):
    story = get_object_or_404(Story, pk=pk)
    return render(request, 'farmer_stories.html', {'story': story})

@login_required
def inbox(request):
    conversations = Conversation.objects.filter(participants=request.user)
    return render(request, 'connect/inbox.html', {'conversations': conversations})

@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    messages = conversation.messages.all()
    other_participant = conversation.get_other_participant(request.user)
    
    # Mark messages as read
    messages.filter(sender=other_participant, is_read=False).update(is_read=True)
    
    return render(request, 'connect/conversation.html', {
        'conversation': conversation,
        'messages': messages,
        'other_participant': other_participant
    })

@login_required
def start_conversation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Check if user is part of the order
    if request.user not in [order.buyer, order.seller, order.boda_rider]:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'})
    
    # Find or create conversation
    conversation = Conversation.objects.filter(
        order=order,
        participants=request.user
    ).first()
    
    if not conversation:
        conversation = Conversation.objects.create(order=order)
        # Add participants based on user role
        if request.user == order.buyer:
            conversation.participants.add(request.user, order.seller)
        elif request.user == order.seller:
            if order.delivery_type == 'boda' and order.boda_rider:
                conversation.participants.add(request.user, order.boda_rider)
            else:
                conversation.participants.add(request.user, order.buyer)
        elif request.user == order.boda_rider:
            conversation.participants.add(request.user, order.seller)
    
    return redirect('conversation_detail', conversation_id=conversation.id)

@login_required
def get_unread_count(request):
    unread_count = Message.objects.filter(
        conversation__participants=request.user,
        sender__is_not=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({'unread_count': unread_count})

@login_required
def check_new_messages(request):
    conversation_id = request.GET.get('conversation_id')
    last_message_id = request.GET.get('last_message_id')
    
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
        new_messages = Message.objects.filter(
            conversation=conversation,
            id__gt=last_message_id
        ).order_by('created_at')
        
        # Mark messages as read if they're from other participants
        new_messages.filter(sender__is_not=request.user, is_read=False).update(is_read=True)
        
        return JsonResponse({
            'status': 'success',
            'messages': [{
                'id': message.id,
                'content': message.content,
                'sender': message.sender.username,
                'created_at': message.created_at.strftime('%b %d, %Y, %I:%M %p')
            } for message in new_messages]
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')

@login_required
def create_course(request):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to create courses.')
        return redirect('learning_hub')
    
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            course.save()
            messages.success(request, 'Course created successfully!')
            return redirect('course_details', pk=course.pk)
    else:
        form = CourseForm()
    
    return render(request, 'create_course.html', {'form': form})

@login_required
def edit_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if not request.user.is_staff and request.user != course.instructor:
        messages.error(request, 'You do not have permission to edit this course.')
        return redirect('course_details', pk=pk)
    
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated successfully!')
            return redirect('course_details', pk=pk)
    else:
        form = CourseForm(instance=course)
    
    return render(request, 'edit_course.html', {
        'form': form,
        'course': course
    })

@login_required
def add_module(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    if not request.user.is_staff and request.user != course.instructor:
        messages.error(request, 'You do not have permission to add modules to this course.')
        return redirect('course_details', pk=course_pk)
    
    if request.method == 'POST':
        form = CourseModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course
            module.save()
            messages.success(request, 'Module added successfully!')
            return redirect('course_details', pk=course_pk)
    else:
        form = CourseModuleForm()
    
    return render(request, 'add_module.html', {
        'form': form,
        'course': course
    })

@login_required
def edit_module(request, pk):
    module = get_object_or_404(CourseModule, pk=pk)
    if not request.user.is_staff and request.user != module.course.instructor:
        messages.error(request, 'You do not have permission to edit this module.')
        return redirect('course_details', pk=module.course.pk)
    
    if request.method == 'POST':
        form = CourseModuleForm(request.POST, instance=module)
        if form.is_valid():
            form.save()
            messages.success(request, 'Module updated successfully!')
            return redirect('course_details', pk=module.course.pk)
    else:
        form = CourseModuleForm(instance=module)
    
    return render(request, 'edit_module.html', {
        'form': form,
        'module': module
    })

@login_required
def add_content(request, module_pk):
    module = get_object_or_404(CourseModule, pk=module_pk)
    if not request.user.is_staff and request.user != module.course.instructor:
        messages.error(request, 'You do not have permission to add content to this module.')
        return redirect('course_details', pk=module.course.pk)
    
    if request.method == 'POST':
        form = CourseContentForm(request.POST)
        if form.is_valid():
            content = form.save(commit=False)
            content.module = module
            content.save()
            messages.success(request, 'Content added successfully!')
            return redirect('course_details', pk=module.course.pk)
    else:
        form = CourseContentForm()
    
    return render(request, 'add_content.html', {
        'form': form,
        'module': module
    })

@login_required
def edit_content(request, pk):
    content = get_object_or_404(CourseContent, pk=pk)
    if not request.user.is_staff and request.user != content.module.course.instructor:
        messages.error(request, 'You do not have permission to edit this content.')
        return redirect('course_details', pk=content.module.course.pk)
    
    if request.method == 'POST':
        form = CourseContentForm(request.POST, instance=content)
        if form.is_valid():
            form.save()
            messages.success(request, 'Content updated successfully!')
            return redirect('course_details', pk=content.module.course.pk)
    else:
        form = CourseContentForm(instance=content)
    
    return render(request, 'edit_content.html', {
        'form': form,
        'content': content
    })
