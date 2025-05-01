from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from django.db.models import Avg

class User(AbstractUser):
    class Role(models.TextChoices):
        BUYER = 'buyer', _('Buyer')
        SELLER = 'seller', _('Seller')
        BODA_RIDER = 'boda_rider', _('Boda Rider')
        ADMIN = 'admin', _('Admin')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.BUYER,
    )
    phone_number = models.CharField(max_length=15, blank=True)
    location = models.CharField(max_length=255, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    wishlist = models.ManyToManyField('Product', related_name='wishlisted_by', blank=True)
    friends = models.ManyToManyField('self', symmetrical=True, blank=True)
    following = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='followers')
    bio = models.TextField(max_length=500, blank=True)
    cover_photo = models.ImageField(upload_to='cover_photos/', blank=True, null=True)
    
    def is_buyer(self):
        return self.role == self.Role.BUYER
    
    def is_seller(self):
        return self.role == self.Role.SELLER
    
    def is_boda_rider(self):
        return self.role == self.Role.BODA_RIDER

class ProductTag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=50, blank=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=50, unique=True)

    def __str__(self):
        variant_desc = []
        if self.size:
            variant_desc.append(f"Size: {self.size}")
        if self.weight:
            variant_desc.append(f"Weight: {self.weight}g")
        return f"{self.product.name} ({', '.join(variant_desc)})"

class PriceHistory(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-date']

class BulkDiscount(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='bulk_discounts')
    min_quantity = models.PositiveIntegerField()
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    
    class Meta:
        ordering = ['min_quantity']

class Product(models.Model):
    class Category(models.TextChoices):
        DAIRY = 'dairy', _('Dairy')
        SEEDS = 'seeds', _('Seeds')
        LIVESTOCK = 'livestock', _('Livestock')
        VEGETABLES = 'vegetables', _('Vegetables')
        FRUITS = 'fruits', _('Fruits')
        GRAINS = 'grains', _('Grains')
        OTHER = 'other', _('Other')

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=20)  # e.g., kg, piece, dozen
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_available = models.BooleanField(default=True)
    tags = models.ManyToManyField(ProductTag, blank=True, related_name='products')
    seasonal_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    seasonal_start = models.DateField(null=True, blank=True)
    seasonal_end = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    min_order_quantity = models.PositiveIntegerField(default=1)
    max_order_quantity = models.PositiveIntegerField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    
    def update_rating_stats(self):
        reviews = self.reviews.all()
        if reviews:
            self.average_rating = reviews.aggregate(Avg('rating'))['rating__avg']
            self.total_reviews = reviews.count()
            self.save()
    
    def get_current_price(self):
        if self.seasonal_price and self.seasonal_start and self.seasonal_end:
            today = timezone.now().date()
            if self.seasonal_start <= today <= self.seasonal_end:
                return self.seasonal_price
        return self.price
    
    def increment_views(self):
        self.views_count += 1
        self.save()
    
    def is_low_stock(self):
        return self.quantity > 0 and self.quantity <= 5
    
    def get_bulk_discount(self, quantity):
        discount = self.bulk_discounts.filter(min_quantity__lte=quantity).order_by('-min_quantity').first()
        if discount:
            return (self.get_current_price() * discount.discount_percentage) / 100
        return 0

    def __str__(self):
        return f"{self.name} - {self.seller.username}"

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        CONFIRMED = 'confirmed', _('Confirmed')
        PROCESSING = 'processing', _('Processing')
        SHIPPED = 'shipped', _('Shipped')
        DELIVERED = 'delivered', _('Delivered')
        CANCELLED = 'cancelled', _('Cancelled')

    class DeliveryType(models.TextChoices):
        BODA = 'boda', _('Boda Delivery')
        SELLER = 'seller', _('Seller Delivery')
        PICKUP = 'pickup', _('Self Pickup')

    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    delivery_type = models.CharField(max_length=20, choices=DeliveryType.choices)
    boda_rider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivery_address = models.TextField()
    payment_status = models.BooleanField(default=False)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

class Cart(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey('ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    class Meta:
        unique_together = ('cart', 'product', 'variant')

class Negotiation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        ACCEPTED = 'accepted', _('Accepted')
        REJECTED = 'rejected', _('Rejected')
        EXPIRED = 'expired', _('Expired')

    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='buyer_negotiations')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='seller_negotiations')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    initial_price = models.DecimalField(max_digits=10, decimal_places=2)
    proposed_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

class Review(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('buyer', 'product')

class Discussion(models.Model):
    CATEGORY_CHOICES = [
        ('organic_farming', 'Organic Farming'),
        ('pest_control', 'Pest Control'),
        ('market_trends', 'Market Trends'),
        ('climate_advice', 'Climate Advice'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    tags = models.CharField(max_length=200, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)
    likes = models.ManyToManyField(User, related_name='liked_discussions', blank=True)
    is_featured = models.BooleanField(default=False)
    is_expert_tip = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('discussion_details', kwargs={'pk': self.pk})
    
    def get_comment_count(self):
        return self.comments.count()
    
    def get_like_count(self):
        return self.likes.count()

class DiscussionImage(models.Model):
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='discussion_images/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f'Image for discussion {self.discussion.title}'

class Comment(models.Model):
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f'Comment by {self.author.get_full_name()} on {self.discussion.title}'

class Story(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='stories/', blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_featured = models.BooleanField(default=False)
    likes = models.ManyToManyField(User, related_name='liked_stories', blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Stories'
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('story_details', kwargs={'pk': self.pk})
    
    def get_like_count(self):
        return self.likes.count()

class Event(models.Model):
    EVENT_TYPE_CHOICES = [
        ('webinar', 'Webinar'),
        ('meetup', 'Local Meetup'),
        ('forum', 'Online Forum'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    online_link = models.URLField(blank=True)
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_date']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('event_details', kwargs={'pk': self.pk})
    
    def get_registered_count(self):
        return self.registrations.count()
    
    def is_full(self):
        if self.max_participants:
            return self.get_registered_count() >= self.max_participants
        return False

class EventRegistration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')
    registered_at = models.DateTimeField(auto_now_add=True)
    reminder_sent = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('event', 'user')
    
    def __str__(self):
        return f'{self.user.get_full_name()} - {self.event.title}'

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    conversation = models.ForeignKey('Conversation', on_delete=models.CASCADE, related_name='messages')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Message from {self.sender.get_full_name()} to {self.recipient.get_full_name()}'
    
    def mark_as_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.save()

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversation_last_message')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversation')

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation {self.id} - {', '.join(user.username for user in self.participants.all())}"

    def get_unread_count(self, user):
        return self.message_set.filter(recipient=user, read_at__isnull=True).count()

class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ('abuse', 'Abuse'),
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('other', 'Other'),
    ]
    
    REPORTED_MODEL_CHOICES = [
        ('discussion', 'Discussion'),
        ('comment', 'Comment'),
        ('story', 'Story'),
        ('message', 'Message'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    reported_model = models.CharField(max_length=20, choices=REPORTED_MODEL_CHOICES)
    reported_id = models.PositiveIntegerField()
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_reports')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Report by {self.reporter.get_full_name()} - {self.get_report_type_display()}'

# Learning Hub Models
class Course(models.Model):
    class Level(models.TextChoices):
        BEGINNER = 'beginner', _('Beginner')
        INTERMEDIATE = 'intermediate', _('Intermediate')
        ADVANCED = 'advanced', _('Advanced')

    title = models.CharField(max_length=200)
    description = models.TextField()
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('course_details', kwargs={'pk': self.pk})

class CourseModule(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class CourseContent(models.Model):
    class ContentType(models.TextChoices):
        VIDEO = 'video', _('Video')
        TEXT = 'text', _('Text')
        QUIZ = 'quiz', _('Quiz')
        ASSIGNMENT = 'assignment', _('Assignment')

    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='contents')
    title = models.CharField(max_length=200)
    content_type = models.CharField(max_length=20, choices=ContentType.choices)
    content = models.TextField()  # For text content or video URL
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.module.title} - {self.title}"

class Resource(models.Model):
    class ResourceType(models.TextChoices):
        PDF = 'pdf', _('PDF Document')
        VIDEO = 'video', _('Video')
        LINK = 'link', _('External Link')
        TOOL = 'tool', _('Tool or Template')

    title = models.CharField(max_length=200)
    description = models.TextField()
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    file = models.FileField(upload_to='resources/', blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('resource_details', kwargs={'pk': self.pk})

class LearningProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_progress')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='progress')
    completed_modules = models.ManyToManyField(CourseModule, blank=True)
    completed_contents = models.ManyToManyField(CourseContent, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    is_completed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('user', 'course')
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title}"

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    images = models.ManyToManyField('PostImage', related_name='posts_with_image', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    shared_discussion = models.ForeignKey(Discussion, on_delete=models.SET_NULL, null=True, blank=True, related_name='shared_in_posts')
    shared_story = models.ForeignKey('Story', on_delete=models.SET_NULL, null=True, blank=True, related_name='shared_in_posts')
    shared_post = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='shared_in_posts')
    privacy = models.CharField(max_length=20, choices=[
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
    ], default='public')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Post by {self.author.get_full_name()} on {self.created_at}'

    def get_like_count(self):
        return self.likes.count()

    def get_comment_count(self):
        return self.post_comments.count()

class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_images')
    image = models.ImageField(upload_to='post_images/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f'Image for post {self.post.id}'

class PostComment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(User, related_name='liked_post_comments', blank=True)
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author.get_full_name()} on {self.post}'

    def get_like_count(self):
        return self.likes.count()

    def get_replies_count(self):
        return self.replies.count()

class FriendRequest(models.Model):
    from_user = models.ForeignKey(User, related_name='sent_friend_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_friend_requests', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user')
        
    def __str__(self):
        return f"{self.from_user.get_full_name()} -> {self.to_user.get_full_name()}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}..."
