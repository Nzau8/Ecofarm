import requests
from django.conf import settings
from base64 import b64encode
from datetime import datetime
import json

class MpesaClient:
    def __init__(self):
        self.business_shortcode = settings.MPESA_BUSINESS_SHORTCODE
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        
        if settings.MPESA_ENVIRONMENT == 'sandbox':
            self.base_url = "https://sandbox.safaricom.co.ke"
        else:
            self.base_url = "https://api.safaricom.co.ke"
    
    def get_access_token(self):
        """Get OAuth access token from Safaricom"""
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        auth = b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        headers = {"Authorization": f"Basic {auth}"}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()["access_token"]
        except Exception as e:
            raise Exception(f"Failed to get access token: {str(e)}")

    def generate_password(self):
        """Generate password for STK push"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{self.business_shortcode}{self.passkey}{timestamp}"
        return b64encode(password_str.encode()).decode(), timestamp

    def stk_push(self, phone_number, amount, account_reference, description):
        """Initiate STK push transaction"""
        access_token = self.get_access_token()
        password, timestamp = self.generate_password()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "BusinessShortCode": self.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": int(phone_number),
            "PartyB": self.business_shortcode,
            "PhoneNumber": int(phone_number),
            "CallBackURL": f"{settings.BASE_URL}/api/mpesa/callback/",
            "AccountReference": account_reference,
            "TransactionDesc": description
        }
        
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"STK push failed: {str(e)}")

    def b2c_payment(self, phone_number, amount, occasion):
        """Send money to customer (B2C)"""
        access_token = self.get_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "InitiatorName": settings.MPESA_B2C_INITIATOR,
            "SecurityCredential": settings.MPESA_B2C_PASSWORD,
            "CommandID": "BusinessPayment",
            "Amount": int(amount),
            "PartyA": self.business_shortcode,
            "PartyB": int(phone_number),
            "Remarks": "Payment",
            "QueueTimeOutURL": f"{settings.BASE_URL}/api/mpesa/b2c/timeout",
            "ResultURL": f"{settings.BASE_URL}/api/mpesa/b2c/result",
            "Occasion": occasion
        }
        
        url = f"{self.base_url}/mpesa/b2c/v1/paymentrequest"
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"B2C payment failed: {str(e)}")

def process_split_payment(order):
    """Process payment with splits between seller and boda rider"""
    mpesa = MpesaClient()
    
    # Calculate amounts
    seller_amount = order.get_items_total()
    delivery_fee = order.get_delivery_fee()
    total_amount = seller_amount + delivery_fee
    
    try:
        # First collect total amount from buyer
        stk_result = mpesa.stk_push(
            phone_number=order.buyer.phone_number,
            amount=total_amount,
            account_reference=f"Order #{order.id}",
            description="Payment for order"
        )
        
        if stk_result.get("ResponseCode") == "0":
            # Payment successful, now distribute to seller and rider
            if order.delivery_type == 'boda' and order.boda_rider:
                # Pay seller
                mpesa.b2c_payment(
                    phone_number=order.seller.phone_number,
                    amount=seller_amount,
                    occasion=f"Payment for order #{order.id}"
                )
                
                # Pay rider
                mpesa.b2c_payment(
                    phone_number=order.boda_rider.phone_number,
                    amount=delivery_fee,
                    occasion=f"Delivery fee for order #{order.id}"
                )
            else:
                # Pay only seller if self-pickup
                mpesa.b2c_payment(
                    phone_number=order.seller.phone_number,
                    amount=seller_amount,
                    occasion=f"Payment for order #{order.id}"
                )
            
            return True, "Payment processed successfully"
    except Exception as e:
        return False, str(e) 