import requests
import logging
from datetime import datetime
import clicksend_client
from clicksend_client import SmsMessage
from clicksend_client.rest import ApiException

SQUARE_ACCESS_TOKEN = 'EAAAl8BNenn5gQ5-esPM1Dnl33MwQLPliryfgXiqzpBR47e_6YBxtd7DvEn-z0z3'
CLICKSEND_USERNAME = 'moathabdulrazak12@gmail.com'
CLICKSEND_API_KEY = 'E9CFB62C-C706-64CF-EF5E-A150DA4124D8'
SPECIFIC_PHONE_NUMBER = '+12087130507'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

headers = {
    'Square-Version': '2024-05-15',
    'Authorization': f'Bearer {SQUARE_ACCESS_TOKEN}',
    'Content-Type': 'application/json'
}

def create_discount():
    url = 'https://connect.squareup.com/v2/catalog/object'
    body = {
        "idempotency_key": str(datetime.now().timestamp()),
        "object": {
            "type": "DISCOUNT",
            "id": "#discount",
            "discount_data": {
                "name": "$5 Off",
                "discount_type": "FIXED_AMOUNT",
                "amount_money": {
                    "amount": 500,  # $5.00
                    "currency": "USD"
                },
                "pin_required": False
            }
        }
    }
    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        discount_id = response.json()['catalog_object']['id']
        logger.info(f"Discount created successfully with ID: {discount_id}")
        return discount_id
    else:
        logger.error(f"Error creating discount: {response.status_code} {response.text}")
        return None

def get_customer_id_by_phone(phone_number):
    url = 'https://connect.squareup.com/v2/customers/search'
    body = {
        "query": {
            "filter": {
                "phone_number": {
                    "exact": phone_number
                }
            }
        }
    }
    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        customers = response.json().get('customers', [])
        if customers:
            customer_id = customers[0]['id']
            logger.info(f"Customer found with ID: {customer_id}")
            return customer_id
        else:
            logger.info(f"No customer found with phone number {phone_number}")
            return None
    else:
        logger.error(f"Error searching for customer: {response.status_code} {response.text}")
        return None

def send_sms(phone_number, message):
    if message.startswith("ClickSend: "):
        message = message[10:]
    
    max_length = 160 - 10
    if len(message) > max_length:
        message = message[:max_length]
    
    logger.info(f"Preparing to send message: {message}")

    configuration = clicksend_client.Configuration()
    configuration.username = CLICKSEND_USERNAME
    configuration.password = CLICKSEND_API_KEY
    
    api_instance = clicksend_client.SMSApi(clicksend_client.ApiClient(configuration))
    sms_message = SmsMessage(
        source="CustomSource",
        body=message,
        to=phone_number
    )
    sms_messages = clicksend_client.SmsMessageCollection(messages=[sms_message])
    
    try:
        api_response = api_instance.sms_send_post(sms_messages)
        logger.info(f"SMS sent successfully to {phone_number}: {api_response}")
    except ApiException as e:
        logger.error(f"Error sending SMS to {phone_number}: {e}")

def main():
    logger.info("Starting process to create discount and send SMS...")
    discount_id = create_discount()
    if discount_id:
        customer_id = get_customer_id_by_phone(SPECIFIC_PHONE_NUMBER)
        if customer_id:
            logger.info(f"Customer ID: {customer_id}")
            send_sms(SPECIFIC_PHONE_NUMBER, f"STORMY VAPE - Long time no see! We've added a $5 discount to your account. Just provide your phone number at checkout to apply the discount.")
        else:
            logger.info("Customer not found. SMS will not be sent.")
    else:
        logger.info("Failed to create discount. Process will not continue.")
    logger.info("Process completed.")

if __name__ == "__main__":
    main()
