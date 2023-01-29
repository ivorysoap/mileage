# Navigate to the package/ directory before importing
import os,sys
sys.path.append(os.path.join(os.path.dirname(__file__), "package"))

import json
import boto3
import base64
from botocore.exceptions import ClientError
import datetime
import pymysql
import uuid

print("Starting secrets manager connection...")

# Secrets Manager connection
secret_name = os.environ['DB_CREDENTIALS_SECRET_NAME']
region_name = "us-east-1"
session = boto3.session.Session()
client = session.client(
    service_name='secretsmanager',
    region_name=region_name
)

try:
    get_secret_value_response = client.get_secret_value(
        SecretId=secret_name
    )
except ClientError as e:
    print(f"Caught exception while retriving secrets from Secrets Manager: {e}.  Exiting...")
    exit()
else:
    # Decrypts secret using the associated KMS key.
    secret = json.loads(get_secret_value_response['SecretString'])

print("Got secrets.  Starting pinpoint connection...")

# Pinpoint connection
pinpoint = boto3.client('pinpoint')

print("Pinpoint ok.  Starting DB connection...")

# Database connection
connection = pymysql.connect(host = secret['host'],
                             user = secret['username'],
                             password = secret['password'],
                             database = secret['dbname'],
                             cursorclass=pymysql.cursors.DictCursor)
print("Got connection ok.  Creating cursor...")
cursor = connection.cursor()
print("Created cursor")

def sendMessage(requesterNumber, message):
    response = pinpoint.send_messages(
        ApplicationId = os.environ['PINPOINT_APP_ID'],
        MessageRequest={
            'Addresses': {
                requesterNumber: {'ChannelType': 'SMS'}
            },
            'MessageConfiguration': {
                'SMSMessage': {
                    'Body': message,
                    'MessageType': 'PROMOTIONAL'
                }
            }
        }
    )


def lambda_handler(event, context):

    usageMessage = "Usage: [vehicleName] gasPrice volumeFilled kmDriven [notes]"

    print(f"Event: {event}")
    
    messagePayload = json.loads(event['Records'][0]['Sns']['Message'])['messageBody']
    requesterNumber = json.loads(event['Records'][0]['Sns']['Message'])['originationNumber']
    print(f"Received message from {requesterNumber}: {messagePayload}")
    
    params = messagePayload.split()

    if len(params) < 3 or len(params) > 5:

        sendMessage(requesterNumber, usageMessage)
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid usage')
        }

    elif len(params) == 3:

        price = params[0]    # Price in $/L
        volume = params[1]   # Volume filled in L
        distance = params[2] # Distance travelled in km

        # Verify correct types
        if not (price[0].isdigit() and volume[0].isdigit() and distance[0].isdigit()):

            sendMessage(requesterNumber, usageMessage)
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid usage')
            } 

        vehicleName = os.environ['DEFAULT_VEHICLE'] if 'DEFAULT_VEHICLE' in os.environ else ""
        notes = ""

    elif len(params) == 4:

        # Two options - has optional param sheetName, or optional param Notes
        if not params[0][0].isdigit() and params[-1][0].isdigit():

            vehicleName = params[0]  # Name of sheet/vehicle
            price = params[1]        # Price in $/L
            volume = params[2]       # Volume filled in L
            distance = params[3]     # Distance travelled in km

            notes = ""

        elif params[0][0].isdigit() and not params[-1][0].isdigit():

            price = params[0]    # Price in $/L
            volume = params[1]   # Volume filled in L
            distance = params[2] # Distance travelled in km
            notes = params[3]    # String with notes

            vehicleName = os.environ['DEFAULT_VEHICLE'] if 'DEFAULT_VEHICLE' in os.environ else ""

        else:
            
            sendMessage(requesterNumber, usageMessage)
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid usage')
            }

    elif len(params) == 5:

        vehicleName = params[0]  # Name of sheet/vehicle
        price = params[1]        # Price in $/L
        volume = params[2]       # Volume filled in L
        distance = params[3]     # Distance travelled in km
        notes = params[4]    # String with notes

        # Verify correct types
        if not (not vehicleName[0].isdigit() and price[0].isdigit() and volume[0].isdigit() and distance[0].isdigit() and not notes[0].isdigit()):

            sendMessage(requesterNumber, usageMessage)
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid usage')
            }

    # Generate ISO 8601 date
    now = datetime.datetime.now().strftime("%Y-%m-%d")

    # Generate UUID
    recordUuid = str(uuid.uuid4())

    try:

        sql = "INSERT INTO `mileage`.`records` (`uuid`, `date`, `fuelPrice`, `volumeFilled`, `distanceDriven`, `notes`) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, (recordUuid, now, price, volume, distance, notes))
        connection.commit()

    except Exception as e:
        sendMessage(requesterNumber, message=f'Caught exception: {e}')
        return {
            'statusCode': 400,
            'body': json.dumps(f'Caught exception: {e}')
        }

    else:
        sendMessage(requesterNumber, message='Successfully added fuel record')
        return {
            'statusCode': 200,
            'body': json.dumps('Successfully added fuel record')
        }


