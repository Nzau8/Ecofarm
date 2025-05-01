from django.urls import path
from django.contrib.auth.views import LogoutView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from . import views

urlpatterns = [
    # Base URLs
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    
    # Authentication URLs
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/', views.user_profile, name='profile'),
    path('profile/update-picture/', views.update_profile_picture, name='update_profile_picture'),
    path('profile/update-cover/', views.update_cover_photo, name='update_cover_photo'),
    
    # Password Reset URLs
    path('password-reset/', PasswordResetView.as_view(
        template_name='password_reset.html',
        email_template_name='password_reset_email.html',
        success_url='/password-reset/done/'
    ), name='password_reset'),
    path('password-reset/done/', PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        success_url='/password-reset/complete/'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),

    # Notification URLs
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),

    # Marketplace URLs
    path('marketplace/', views.marketplace, name='marketplace'),
    path('search/', views.search_results, name='search_results'),

    # Product URLs
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('product/<int:pk>/edit/', views.edit_product, name='edit_product'),
    path('product/<int:pk>/view/', views.track_product_view, name='track_product_view'),
    path('product/<int:pk>/variants/', views.product_variants, name='product_variants'),
    path('product/variant/<int:pk>/delete/', views.delete_variant, name='delete_variant'),
    path('product/review/<int:pk>/delete/', views.delete_review, name='delete_review'),
    path('product/<int:pk>/bulk-discount/', views.create_bulk_discount, name='create_bulk_discount'),
    path('product/bulk-discount/<int:pk>/delete/', views.delete_bulk_discount, name='delete_bulk_discount'),
    path('product/tags/', views.manage_tags, name='manage_tags'),
    path('product/tag/<int:pk>/delete/', views.delete_tag, name='delete_tag'),
    path('product/<int:pk>/quick-view/', views.quick_view, name='product_quick_view'),

    # Cart and Wishlist URLs
    path('cart/', views.cart, name='cart'),
    path('cart/select-rider/', views.select_rider, name='select_rider'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('add-to-wishlist/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove-from-wishlist/', views.remove_from_wishlist, name='remove_from_wishlist'),

    # Order URLs
    path('checkout/', views.checkout, name='checkout'),
    path('order/<int:pk>/confirmation/', views.order_confirmation, name='order_confirmation'),
    path('order/<int:pk>/tracking/', views.delivery_tracking, name='delivery_tracking'),
    path('order/<int:pk>/confirm-delivery/', views.confirm_delivery, name='confirm_delivery'),

    # Dashboard URLs
    path('seller-dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('buyer-dashboard/', views.buyer_dashboard, name='buyer_dashboard'),
    path('boda-dashboard/', views.boda_dashboard, name='boda_dashboard'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('add-product/', views.add_product, name='add_product'),
    path('edit-product/<int:pk>/', views.edit_product, name='edit_product'),

    # Negotiation URLs
    path('create-negotiation/', views.create_negotiation, name='create_negotiation'),
    path('negotiation/<int:pk>/respond/', views.respond_to_negotiation, name='respond_to_negotiation'),

    # Social URLs
    path('user/<str:username>/', views.user_profile, name='user_profile'),
    path('friends/', views.friend_list, name='friend_list'),
    path('friends/request/<int:user_id>/', views.send_friend_request, name='send_friend_request'),
    path('friends/accept/<int:request_id>/', views.accept_friend_request, name='accept_friend_request'),
    path('friends/reject/<int:request_id>/', views.reject_friend_request, name='reject_friend_request'),
    path('follow/<int:user_id>/', views.follow_user, name='follow_user'),
    path('unfollow/<int:user_id>/', views.unfollow_user, name='unfollow_user'),

    # Community URLs
    path('community/', views.community, name='community'),
    path('community/rules/', views.community_rules, name='community_rules'),
    path('discussions/', views.community_home, name='discussions'),
    path('discussion/<int:pk>/', views.discussion_details, name='discussion_details'),
    path('discussion/create/', views.create_discussion, name='create_discussion'),
    path('discussion/<int:pk>/edit/', views.edit_discussion, name='edit_discussion'),
    path('discussion/<int:pk>/delete/', views.delete_discussion, name='delete_discussion'),
    path('farmer-stories/', views.farmer_stories, name='farmer_stories'),
    path('farmer-stories/<int:pk>/', views.story_details, name='story_details'),
    path('story/create/', views.create_story, name='create_story'),
    path('story/<int:pk>/edit/', views.edit_story, name='edit_story'),
    path('story/<int:pk>/like/', views.like_story, name='like_story'),
    path('story/<int:pk>/comment/', views.comment_story, name='comment_story'),
    path('events/', views.events, name='events'),
    path('events/<int:pk>/', views.event_details, name='event_details'),
    path('event/<int:pk>/', views.event_details, name='event_details'),

    # Learning Hub URLs
    path('learning-hub/', views.learning_hub, name='learning_hub'),
    path('course/<int:pk>/', views.course_details, name='course_details'),
    path('course/create/', views.create_course, name='create_course'),
    path('course/<int:pk>/edit/', views.edit_course, name='edit_course'),
    path('course/<int:course_pk>/add-module/', views.add_module, name='add_module'),
    path('module/<int:pk>/edit/', views.edit_module, name='edit_module'),
    path('module/<int:module_pk>/add-content/', views.add_content, name='add_content'),
    path('content/<int:pk>/edit/', views.edit_content, name='edit_content'),
    path('resources/', views.resources_list, name='resources_list'),
    path('resource/<int:pk>/', views.resource_details, name='resource_details'),
    path('resource/create/', views.create_resource, name='create_resource'),

    # Report URLs
    path('report/<str:content_type>/<int:content_id>/', views.report_content, name='report_content'),
    path('report/<int:pk>/resolve/', views.resolve_report, name='resolve_report'),

    # Post URLs
    path('post/create/', views.create_post, name='create_post'),
    path('post/<int:pk>/add-image/', views.add_image_to_post, name='add_image_to_post'),
    path('post/<int:pk>/like/', views.like_post, name='like_post'),
    path('post/<int:pk>/comment/', views.add_post_comment, name='add_post_comment'),
    path('comment/<int:pk>/reply/', views.reply_to_comment, name='reply_to_comment'),
    path('post/<int:pk>/share/', views.share_post, name='share_post'),
    path('post/<int:pk>/delete/', views.delete_post, name='delete_post'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('news-feed/', views.news_feed, name='news_feed'),

    # Messaging URLs
    path('inbox/', views.inbox, name='inbox'),
    path('conversation/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('message_seller/', views.message_seller, name='message_seller'),
    path('check_new_messages/', views.check_new_messages, name='check_new_messages'),
    path('start_conversation/<int:order_id>/', views.start_conversation, name='start_conversation'),
    path('unread_count/', views.get_unread_count, name='get_unread_count'),

    # M-Pesa callback URLs
    path('api/mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('api/mpesa/b2c/timeout/', views.mpesa_b2c_timeout, name='mpesa_b2c_timeout'),
    path('api/mpesa/b2c/result/', views.mpesa_b2c_result, name='mpesa_b2c_result'),
]