# Generated by Django 5.1.5 on 2025-05-02 03:25

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('connect', '0012_commentimage_discussionimage_remove_discussion_likes_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='comment',
            name='images',
        ),
        migrations.AlterUniqueTogether(
            name='commentreaction',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='commentreaction',
            name='comment',
        ),
        migrations.RemoveField(
            model_name='commentreaction',
            name='user',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='reactions',
        ),
        migrations.AlterUniqueTogether(
            name='discussionreaction',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='discussionreaction',
            name='discussion',
        ),
        migrations.RemoveField(
            model_name='discussionreaction',
            name='user',
        ),
        migrations.RemoveField(
            model_name='discussion',
            name='reactions',
        ),
        migrations.AlterModelOptions(
            name='message',
            options={'ordering': ['-created_at']},
        ),
        migrations.RemoveField(
            model_name='comment',
            name='mentioned_users',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='parent_comment',
        ),
        migrations.RemoveField(
            model_name='discussion',
            name='images',
        ),
        migrations.RemoveField(
            model_name='discussion',
            name='mentioned_users',
        ),
        migrations.RemoveField(
            model_name='discussion',
            name='privacy',
        ),
        migrations.RemoveField(
            model_name='message',
            name='is_read',
        ),
        migrations.RemoveField(
            model_name='order',
            name='cart_items',
        ),
        migrations.RemoveField(
            model_name='order',
            name='mpesa_checkout_request_id',
        ),
        migrations.RemoveField(
            model_name='order',
            name='mpesa_request_id',
        ),
        migrations.RemoveField(
            model_name='order',
            name='seller',
        ),
        migrations.RemoveField(
            model_name='user',
            name='latitude',
        ),
        migrations.RemoveField(
            model_name='user',
            name='longitude',
        ),
        migrations.AddField(
            model_name='conversation',
            name='last_message',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conversation_last_message', to='connect.message'),
        ),
        migrations.AddField(
            model_name='discussion',
            name='likes',
            field=models.ManyToManyField(blank=True, related_name='liked_discussions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='discussionimage',
            name='discussion',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, related_name='images', to='connect.discussion'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='message',
            name='read_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='message',
            name='recipient',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='received_messages', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='conversation',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conversation', to='connect.order'),
        ),
        migrations.AlterField(
            model_name='order',
            name='boda_rider',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deliveries', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='order',
            name='buyer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='order',
            name='delivery_address',
            field=models.TextField(default=1),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='order',
            name='delivery_type',
            field=models.CharField(choices=[('boda', 'Boda Delivery'), ('seller', 'Seller Delivery'), ('pickup', 'Self Pickup')], max_length=20),
        ),
        migrations.AlterField(
            model_name='order',
            name='payment_status',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('processing', 'Processing'), ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')], default='pending', max_length=20),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='connect.order'),
        ),
        migrations.AlterField(
            model_name='user',
            name='location',
            field=models.CharField(blank=True, default=1, max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='user',
            name='operating_zone',
            field=models.CharField(blank=True, default=1, help_text='Zone where the user operates (for sellers and riders)', max_length=255),
            preserve_default=False,
        ),
        migrations.DeleteModel(
            name='CommentImage',
        ),
        migrations.DeleteModel(
            name='CommentReaction',
        ),
        migrations.DeleteModel(
            name='DiscussionReaction',
        ),
    ]
