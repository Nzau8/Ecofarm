from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import (
    User, Product, ProductImage, Order, OrderItem, Cart, CartItem, Negotiation, 
    Review, Discussion, Comment, Story, Event, EventRegistration, Message, Report, 
    Resource, Post, PostImage, PostComment, ProductVariant, BulkDiscount, ProductTag,
    Course, CourseModule, CourseContent
)

class UserSignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'phone_number', 'location', 'profile_picture')
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': '^(?:254|\+254|0)?([7-9]{1}[0-9]{8})$',
                'placeholder': 'e.g., 0712345678 or 254712345678'
            }),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Remove any non-digit characters
            phone = ''.join(filter(str.isdigit, phone))
            
            # Add country code if not present
            if len(phone) == 9:  # Format: 7XXXXXXXX
                phone = '254' + phone
            elif len(phone) == 10 and phone.startswith('0'):  # Format: 07XXXXXXXX
                phone = '254' + phone[1:]
            elif len(phone) == 12 and phone.startswith('254'):  # Format: 254XXXXXXXXX
                pass
            else:
                raise forms.ValidationError('Invalid phone number format. Use format: 07XXXXXXXX or 254XXXXXXXX')
            
        return phone

class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['size', 'weight', 'price', 'stock', 'sku']
        widgets = {
            'size': forms.TextInput(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
        }

class BulkDiscountForm(forms.ModelForm):
    class Meta:
        model = BulkDiscount
        fields = ['min_quantity', 'discount_percentage']
        widgets = {
            'min_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class ProductTagForm(forms.ModelForm):
    class Meta:
        model = ProductTag
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleImageField(forms.ImageField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class ProductForm(forms.ModelForm):
    images = MultipleImageField(
        required=False,
        help_text='You can select multiple images. The first image will be the primary image.'
    )

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'category', 'price', 'quantity', 'unit',
            'tags', 'seasonal_price', 'seasonal_start', 'seasonal_end',
            'expiry_date', 'min_order_quantity', 'max_order_quantity',
            'is_featured'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': True}),
            'category': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'required': True}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'required': True}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '3'}),
            'seasonal_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'min_order_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'max_order_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'seasonal_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'seasonal_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean_images(self):
        """
        Validate uploaded images
        """
        images = self.files.getlist('images')
        if images:
            for image in images:
                # Validate file size (max 5MB)
                if image.size > 5 * 1024 * 1024:
                    raise forms.ValidationError("Image file too large ( > 5mb )")
                # Validate file type
                if not image.content_type.startswith('image/'):
                    raise forms.ValidationError("Please upload only image files.")
        return images

    def save(self, commit=True):
        product = super().save(commit=False)  # Always use commit=False initially
        if commit:
            product.save()
            self.save_m2m()
            # Handle images only if commit=True
            if self.cleaned_data.get('images'):
                # Delete existing images if new ones are uploaded
                product.images.all().delete()
                # Create new images
                for i, image in enumerate(self.cleaned_data['images']):
                    ProductImage.objects.create(
                        product=product,
                        image=image,
                        is_primary=(i == 0)  # First image is primary
                    )
        return product

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('delivery_type', 'delivery_address')
        widgets = {
            'delivery_type': forms.Select(attrs={'class': 'form-select'}),
            'delivery_address': forms.Textarea(attrs={'rows': 3}),
        }

class NegotiationForm(forms.ModelForm):
    class Meta:
        model = Negotiation
        fields = ('product', 'proposed_price')
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'initial' in kwargs and 'product' in kwargs['initial']:
            product = kwargs['initial']['product']
            self.fields['initial_price'] = forms.DecimalField(
                initial=product.price,
                disabled=True,
                widget=forms.NumberInput(attrs={'class': 'form-control'})
            )

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'comment')
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'step': '1'
            }),
            'comment': forms.Textarea(attrs={'rows': 3}),
        }

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    subject = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}))

class DiscussionForm(forms.ModelForm):
    images = MultipleImageField(
        required=False,
        help_text='You can upload multiple images to support your discussion'
    )
    
    class Meta:
        model = Discussion
        fields = ('title', 'content', 'category', 'tags')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'What would you like to discuss?'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control rich-text-editor',
                'rows': 5,
                'placeholder': 'Share your thoughts, questions, or experiences...'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Add tags separated by commas (e.g., #maize, #greenhouse)'
            }),
        }

class CommentForm(forms.ModelForm):
    images = MultipleImageField(
        required=False,
        help_text='You can upload multiple images with your comment'
    )
    
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control rich-text-editor',
                'rows': 2,
                'placeholder': 'Write a comment...'
            }),
        }

class StoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ('title', 'content', 'image')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your story title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Share your farming success story...'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ('title', 'description', 'event_type', 'start_date', 'end_date', 'location', 'online_link', 'max_participants')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter event title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe the event...'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter event location'}),
            'online_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Enter online meeting link'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Maximum number of participants'}),
        }

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Type your message...'}),
        }

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ('report_type', 'reason')
        widgets = {
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Please explain why you are reporting this content...'}),
        }

class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['title', 'description', 'resource_type', 'file', 'url']

    def clean(self):
        cleaned_data = super().clean()
        resource_type = cleaned_data.get('resource_type')
        file = cleaned_data.get('file')
        url = cleaned_data.get('url')

        if resource_type in ['pdf', 'tool'] and not file:
            raise forms.ValidationError('Please upload a file for PDF documents and tools.')
        elif resource_type == 'video' and not url:
            raise forms.ValidationError('Please provide a URL for video resources.')
        elif resource_type == 'link' and not url:
            raise forms.ValidationError('Please provide a URL for external links.')

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'privacy']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What\'s on your mind?'}),
            'privacy': forms.Select(attrs={'class': 'form-select'}),
        }

class PostImageForm(forms.ModelForm):
    class Meta:
        model = PostImage
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Add a caption...'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

class PostCommentForm(forms.ModelForm):
    class Meta:
        model = PostComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Write a comment...'}),
        }

class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'location', 'bio', 'profile_picture', 'cover_photo')
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Tell us about yourself...'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your location'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': '^(?:254|\+254|0)?([7-9]{1}[0-9]{8})$',
                'placeholder': 'e.g., 0712345678 or 254712345678'
            }),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'cover_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Remove any non-digit characters
            phone = ''.join(filter(str.isdigit, phone))
            
            # Add country code if not present
            if len(phone) == 9:  # Format: 7XXXXXXXX
                phone = '254' + phone
            elif len(phone) == 10 and phone.startswith('0'):  # Format: 07XXXXXXXX
                phone = '254' + phone[1:]
            elif len(phone) == 12 and phone.startswith('254'):  # Format: 254XXXXXXXXX
                pass
            else:
                raise forms.ValidationError('Invalid phone number format. Use format: 07XXXXXXXX or 254XXXXXXXX')
            
        return phone

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'level', 'thumbnail', 'is_published']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'level': forms.Select(attrs={'class': 'form-select'}),
        }

class CourseModuleForm(forms.ModelForm):
    class Meta:
        model = CourseModule
        fields = ['title', 'description', 'order']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'order': forms.NumberInput(attrs={'min': 0}),
        }

class CourseContentForm(forms.ModelForm):
    class Meta:
        model = CourseContent
        fields = ['title', 'content_type', 'content', 'order']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4}),
            'content_type': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'min': 0}),
        }

    def clean_content(self):
        content_type = self.cleaned_data.get('content_type')
        content = self.cleaned_data.get('content')
        
        if content_type == 'video' and not content.startswith(('http://', 'https://')):
            raise forms.ValidationError('Please provide a valid video URL.')
        
        return content