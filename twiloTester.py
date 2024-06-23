import logging
import clicksend_client
from clicksend_client import SmsMessage
from clicksend_client.rest import ApiException

# Configure ClickSend API credentials
CLICKSEND_USERNAME = 'moathabdulrazak12@gmail.com'
CLICKSEND_API_KEY = 'E9CFB62C-C706-64CF-EF5E-A150DA4124D8'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

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

def test_clicksend_sms():
    test_phone_number = '+12087130507'
    test_message = "STORMY VAPE - Long time no see, $5 off your next order! Type your number when you arrive to claim."
    send_sms(test_phone_number, test_message)

if __name__ == "__main__":
    test_clicksend_sms()