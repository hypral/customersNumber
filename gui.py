import requests
from datetime import datetime, timedelta
import logging
from dateutil.parser import parse
import json
import os
import clicksend_client
from clicksend_client import SmsMessage
from clicksend_client.rest import ApiException
import tkinter as tk
from tkinter import messagebox, scrolledtext

SQUARE_ACCESS_TOKEN = 'EAAAl8BNenn5gQ5-esPM1Dnl33MwQLPliryfgXiqzpBR47e_6YBxtd7DvEn-z0z3'
LOCATION_ID = 'LXSE2HFEKBQ97'
CLICKSEND_USERNAME = 'moathabdulrazak12@gmail.com'
CLICKSEND_API_KEY = 'E9CFB62C-C706-64CF-EF5E-A150DA4124D8'
TRACKING_FILE = 'customers_with_discount.json'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

headers = {
    'Square-Version': '2024-05-15',
    'Authorization': f'Bearer {SQUARE_ACCESS_TOKEN}',
    'Content-Type': 'application/json'
}

def load_customers_with_discount():
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r') as f:
            return json.load(f)
    return []

def save_customers_with_discount(customers_with_discount):
    with open(TRACKING_FILE, 'w') as f:
        json.dump(customers_with_discount, f, indent=4)

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
        discount_id = response.json()['object']['id']
        logger.info(f"Discount created successfully with ID: {discount_id}")
        return discount_id
    else:
        logger.error(f"Error creating discount: {response.status_code} {response.text}")
        return None

def add_discount_to_customer(customer_id, discount_id):
    url = f'https://connect.squareup.com/v2/customers/{customer_id}/loyalty/rewards'
    body = {
        "reward": {
            "program_id": discount_id,
            "points": 5
        }
    }
    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        logger.info(f"Discount added successfully to customer {customer_id}")
    else:
        logger.error(f"Error adding discount to customer {customer_id}: {response.status_code} {response.text}")

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

def fetch_and_send_discounts():
    customers_with_discount = load_customers_with_discount()

    logger.info("Fetching customers from Square...")
    customers = fetch_customers()
    logger.info(f"Total customers fetched: {len(customers)}")

    logger.info("Identifying inactive customers...")
    inactive_customers = identify_inactive_customers(customers)
    logger.info(f"Total inactive customers identified: {len(inactive_customers)}")

    save_inactive_customers_to_json(inactive_customers)

    discount_id = create_discount()
    if discount_id:
        for customer in inactive_customers:
            if customer['customerId'] not in customers_with_discount:
                add_discount_to_customer(customer['customerId'], discount_id)
                send_sms(customer['phone'], "STORMY VAPE - Long time no see, here’s $5 off has been added to your next order! Type in your number when you arrive to claim.")
                customers_with_discount.append(customer['customerId'])

    save_customers_with_discount(customers_with_discount)
    messagebox.showinfo("Success", "Discounts and SMS notifications have been sent to inactive customers.")

def create_gui():
    root = tk.Tk()
    root.title("Customer Discount Manager")

    canvas = tk.Canvas(root, height=600, width=800, bg="#263D42")
    canvas.pack()

    frame = tk.Frame(root, bg="white")
    frame.place(relwidth=0.8, relheight=0.8, relx=0.1, rely=0.1)

    title = tk.Label(frame, text="Customer Discount Manager", font=("Helvetica", 24), bg="white")
    title.pack(pady=20)

    fetch_button = tk.Button(frame, text="Fetch and Send Discounts", padx=10, pady=5, fg="white", bg="#263D42", command=fetch_and_send_discounts)
    fetch_button.pack(pady=20)

    log_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, width=80, height=20, font=("Helvetica", 10))
    log_area.pack(pady=20)

    def log_handler(record):
        log_area.insert(tk.END, record.getMessage() + '\n')
        log_area.yview(tk.END)

    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().handlers[-1].setLevel(logging.INFO)
    logging.getLogger().handlers[-1].emit = log_handler

    root.mainloop()

if __name__ == "__main__":
    create_gui()
