import requests
import logging
from datetime import datetime
import json
import uuid

# Square credentials and setup
SQUARE_ACCESS_TOKEN = 'EAAAl8BNenn5gQ5-esPM1Dnl33MwQLPliryfgXiqzpBR47e_6YBxtd7DvEn-z0z3'
SPECIFIC_PHONE_NUMBER = '+12087130507'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

headers = {
    'Square-Version': '2024-06-04',
    'Authorization': f'Bearer {SQUARE_ACCESS_TOKEN}',
    'Content-Type': 'application/json'
}

def log_request_response(method, url, request_body, response):
    logger.info(f"Request: {method} {url}")
    logger.info(f"Request Headers: {json.dumps(headers, indent=2)}")
    logger.info(f"Request Body: {json.dumps(request_body, indent=2)}")
    logger.info(f"Response Status: {response.status_code}")
    logger.info(f"Response Body: {json.dumps(response.json(), indent=2)}")

def get_customer_id_by_phone(phone_number):
    url = 'https://connect.squareup.com/v2/customers/search'
    body = {"query": {"filter": {"phone_number": {"exact": phone_number}}}}
    response = requests.post(url, headers=headers, json=body)
    log_request_response("POST", url, body, response)
    
    if response.status_code == 200 and response.json().get('customers'):
        customer_id = response.json()['customers'][0]['id']
        logger.info(f"Customer found with ID: {customer_id}")
        return customer_id
    else:
        logger.error(f"Failed to find customer by phone number {phone_number}")
        return None

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
            "reason": "Complimentary points"
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
    customer_id = get_customer_id_by_phone(SPECIFIC_PHONE_NUMBER)
    if customer_id:
        loyalty_account_id, current_points = get_loyalty_account_id(customer_id)
        if loyalty_account_id:
            logger.info(f"Existing loyalty account found. Current points balance: {current_points}")
            points_to_add = 30  # Adjust this value as needed
            success = adjust_loyalty_points(loyalty_account_id, points_to_add)
            if success:
                logger.info(f"Successfully added {points_to_add} points. New balance should be {current_points + points_to_add}")
            else:
                logger.error("Failed to add loyalty points. Please check the logs for details.")
        else:
            logger.error("Loyalty account could not be retrieved.")
    else:
        logger.error("Customer ID could not be retrieved or does not exist.")

if __name__ == "__main__":
    main()