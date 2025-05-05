import logging
from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

def send_whatsapp_message(to_number, message):
    """
    Send a WhatsApp message using Twilio
    Args:
        to_number (str): The recipient's phone number in E.164 format
        message (str): The message to send
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        # Initialize Twilio client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Format the 'to' number to ensure it's in E.164 format
        if not to_number.startswith('+'):
            to_number = '+' + to_number
        
        # Send message through Twilio
        message = client.messages.create(
            from_=f'whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}',
            body=message,
            to=f'whatsapp:{to_number}'
        )
        
        logger.info(f"WhatsApp message sent successfully. SID: {message.sid}")
        return True, None
        
    except TwilioRestException as e:
        error_msg = f"Failed to send WhatsApp message: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error sending WhatsApp message: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def format_order_notification(order):
    """
    Format order details for WhatsApp notification
    Args:
        order: Order instance
    Returns:
        str: Formatted message
    """
    items_list = "\n".join([
        f"- {item.quantity}x {item.product.name} @ KES {item.price_at_time} each"
        for item in order.items.all()
    ])
    
    message = f"""
New Order #{order.id}!

Buyer: {order.buyer.get_full_name()}
Phone: {order.buyer.phone_number}
Total Amount: KES {order.total_amount}

Items:
{items_list}

Delivery Type: {order.get_delivery_type_display()}
"""
    
    if order.delivery_type == 'pickup':
        message += "\nCustomer will pick up the order."
    
    return message.strip() 