from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from django.db.models import Count
from .models import (
    User, Product, ProductImage, Order, OrderItem, Cart, CartItem,
    Negotiation, Review, Discussion, Comment, Story, Event,
    EventRegistration, Message, Report, Course, CourseModule,
    CourseContent, Resource, LearningProgress
)

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone_number', 'location', 'profile_picture', 'wishlist')}),
    )

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'seller', 'price', 'category', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'description')

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'delivery_type')
    search_fields = ('buyer__username', 'delivery_address')

class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'level', 'is_published')
    list_filter = ('level', 'is_published')
    search_fields = ('title', 'description')

class DiscussionAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'created_at')
    list_filter = ('category', 'is_featured', 'is_expert_tip')
    search_fields = ('title', 'content')

class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'resource_type', 'created_at', 'get_file_or_url')
    list_filter = ('resource_type', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'resource_type')
        }),
        ('Resource Content', {
            'fields': ('file', 'url'),
            'description': 'Upload a file for PDFs and tools, or provide a URL for videos and external links.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_file_or_url(self, obj):
        if (obj.file):
            return f'File: {obj.file.name}'
        elif (obj.url):
            return f'URL: {obj.url}'
        return '-'
    get_file_or_url.short_description = 'Resource Location'

class CustomAdminSite(admin.AdminSite):
    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        return app_list

    def index(self, request, extra_context=None):
        # Get statistics
        extra_context = extra_context or {}
        extra_context['total_users'] = User.objects.count()
        extra_context['total_discussions'] = Discussion.objects.count()
        extra_context['total_products'] = Product.objects.count()
        extra_context['total_orders'] = Order.objects.count()
        
        return super().index(request, extra_context)

# Create the custom admin site instance
admin_site = CustomAdminSite(name='admin')

# Register models with the custom admin site
admin_site.register(User, CustomUserAdmin)
admin_site.register(Group)  # Don't forget to register the Group model
admin_site.register(Product, ProductAdmin)
admin_site.register(ProductImage)
admin_site.register(Order, OrderAdmin)
admin_site.register(OrderItem)
admin_site.register(Cart)
admin_site.register(CartItem)
admin_site.register(Negotiation)
admin_site.register(Review)
admin_site.register(Discussion, DiscussionAdmin)
admin_site.register(Comment)
admin_site.register(Story)
admin_site.register(Event)
admin_site.register(EventRegistration)
admin_site.register(Message)
admin_site.register(Report)
admin_site.register(Course, CourseAdmin)
admin_site.register(CourseModule)
admin_site.register(CourseContent)
admin_site.register(Resource, ResourceAdmin)
admin_site.register(LearningProgress)
