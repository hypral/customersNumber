import requests
from datetime import datetime, timedelta
import logging
from dateutil.parser import parse
import json
import os
import uuid
import clicksend_client
from clicksend_client import SmsMessage
from clicksend_client.rest import ApiException

# Configuration
SQUARE_ACCESS_TOKEN = 'EAAAl8BNenn5gQ5-esPM1Dnl33MwQLPliryfgXiqzpBR47e_6YBxtd7DvEn-z0z3'
LOCATION_ID = 'LXSE2HFEKBQ97'
CLICKSEND_USERNAME = 'moathabdulrazak12@gmail.com'
CLICKSEND_API_KEY = 'E9CFB62C-C706-64CF-EF5E-A150DA4124D8'
TRACKING_FILE = 'customers_with_points.json'

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

headers = { 
    'Square-Version': '2024-05-15',
    'Authorization': f'Bearer {SQUARE_ACCESS_TOKEN}',
    'Content-Type': 'application/json'
}

def log_request_response(method, url, request_body, response):
    logger.info(f"Request: {method} {url}")
    logger.info(f"Request Headers: {json.dumps(headers, indent=2)}")
    logger.info(f"Request Body: {json.dumps(request_body, indent=2)}")
    logger.info(f"Response Status: {response.status_code}")
    logger.info(f"Response Body: {json.dumps(response.json(), indent=2)}")

def load_customers_with_points():
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r') as f:
            return json.load(f)
    return []

def save_customers_with_points(customers_with_points):
    with open(TRACKING_FILE, 'w') as f:
        json.dump(customers_with_points, f, indent=4)

def fetch_customers():
    url = 'https://connect.squareup.com/v2/customers'
    customers = []
    cursor = None
    while True:
        params = {}
        if cursor:
            params['cursor'] = cursor
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            customers.extend(data.get('customers', []))
            cursor = data.get('cursor', None)
            if not cursor:
                break
        else:
            logger.error(f"Error fetching customers: {response.status_code} {response.text}")
            break
    return customers

def fetch_orders(customer_id):
    url = 'https://connect.squareup.com/v2/orders/search'
    orders = []
    body = {
        "location_ids": [LOCATION_ID],
        "query": {
            "filter": {
                "customer_filter": {
                    "customer_ids": [customer_id]
                }
            }
        }
    }
    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        orders = response.json().get('orders', [])
    else:
        logger.error(f"Error fetching orders for customer {customer_id}: {response.status_code} {response.text}")
    return orders

def identify_inactive_customers(customers, months=2):
    inactive_customers = []
    cutoff_date = datetime.now().astimezone() - timedelta(days=months*30)
    
    for customer in customers:
        if customer.get('phone_number', 'N/A') == 'N/A':
            continue

        orders = fetch_orders(customer['id'])
        last_purchase_date = None
        
        for order in orders:
            try:
                purchase_date = parse(order['created_at'])
                if last_purchase_date is None or purchase_date > last_purchase_date:
                    last_purchase_date = purchase_date
            except ValueError as e:
                logger.error(f"Error parsing date for order {order['id']}: {e}")
                continue
        
        if last_purchase_date and last_purchase_date < cutoff_date:
            customer_info = {
                'customerId': customer['id'],
                'phone': customer.get('phone_number', 'N/A'),
                'last_purchase': last_purchase_date.strftime('%Y-%m-%d %H:%M:%S')
            }
            inactive_customers.append(customer_info)
            logger.info(f"Inactive Customer: {customer_info['customerId']}, Phone: {customer_info['phone']}, Last Purchase: {customer_info['last_purchase']}")
    
    return inactive_customers

def save_inactive_customers_to_json(inactive_customers, filename='inactive_customers.json'):
    with open(filename, 'w') as f:
        json.dump(inactive_customers, f, indent=4)
    logger.info(f"Inactive customers saved to {filename}")

def send_sms(phone_number, message):
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

def get_loyalty_account_id(customer_id):
    url = 'https://connect.squareup.com/v2/loyalty/accounts/search'
    body = {"query": {"customer_ids": [customer_id]}}
    response = requests.post(url, headers=headers, json=body)
    log_request_response("POST", url, body, response)
    
    if response.status_code == 200 and response.json().get('loyalty_accounts'):
        loyalty_account = response.json()['loyalty_accounts'][0]
        loyalty_account_id = loyalty_account['id']
        points = loyalty_account.get('balance', 0)
        logger.info(f"Loyalty account found with ID: {loyalty_account_id}, Points balance: {points}")
        return loyalty_account_id, points
    else:
        logger.info(f"No loyalty account found for customer ID {customer_id}")
        return None, 0

def adjust_loyalty_points(loyalty_account_id, points):
    url = f'https://connect.squareup.com/v2/loyalty/accounts/{loyalty_account_id}/adjust'
    body = {
        "idempotency_key": str(uuid.uuid4()),
        "adjust_points": {
            "points": points,
            "reason": "Complimentary points for inactive customers"
        }
    }
    response = requests.post(url, headers=headers, json=body)
    log_request_response("POST", url, body, response)
    
    if response.status_code == 200:
        logger.info(f"Successfully adjusted {points} points for loyalty account ID {loyalty_account_id}")
        return True
    else:
        logger.error(f"Failed to adjust points for loyalty account ID {loyalty_account_id}")
        return False

def main():
    logger.info("Fetching customers from Square...")
    customers = fetch_customers()

    logger.info(f"Total customers fetched: {len(customers)}")

    logger.info("Identifying inactive customers...")
    inactive_customers = identify_inactive_customers(customers)

    logger.info(f"Total inactive customers identified: {len(inactive_customers)}")

    save_inactive_customers_to_json(inactive_customers)

    customers_with_points = load_customers_with_points()

    for customer in inactive_customers:
        if customer['customerId'] not in customers_with_points:
            loyalty_account_id, current_points = get_loyalty_account_id(customer['customerId'])
            if loyalty_account_id:
                points_to_add = 30  # Adjust this value as needed
                points_added = adjust_loyalty_points(loyalty_account_id, points_to_add)
                if points_added:
                    logger.info(f"Successfully added {points_to_add} points to customer {customer['customerId']}. New balance should be {current_points + points_to_add}")
                    send_sms(customer['phone'], f"STORMY- Long time no see! We've added {points_to_add} loyalty points to your account. Visit us soon to use them!")
                    customers_with_points.append(customer['customerId'])
                else:
                    logger.error(f"Failed to add loyalty points for customer {customer['customerId']}. No SMS sent.")
            else:
                logger.error(f"No loyalty account found for customer {customer['customerId']}. No points added or SMS sent.")

    save_customers_with_points(customers_with_points)

    for customer in inactive_customers:
        print(f"Customer ID: {customer['customerId']}, Phone: {customer['phone']}, Last Purchase: {customer['last_purchase']}")

if __name__ == "__main__":
    main()