import json
import os
import boto3
from infmon.io import (
    get_contract_abi, get_event_interface, get_current_block, get_contract_events
)


ENV = 'dev'
APP = 'crypto-monitor'

ssm = boto3.client('ssm')
params = ssm.get_parameters_by_path(
    Path=f'/{ENV}/{APP}',
    WithDecryption=True
)
kv_pairs = {p['Name']: p['Value'] for p in params['Parameters']}

INFURA_PROJECT_ID = kv_pairs[f'/{ENV}/{APP}/infura-project-id']
ETHERSCAN_API_KEY = kv_pairs[f'/{ENV}/{APP}/etherscan-api-key']

# NB: remember to whitelist address in Infura project settings is using whitelisting
token_address = os.environ.get('CONTRACT_ADDRESS', '0xdAC17F958D2ee523a2206206994597C13D831ec7')  # Tether
NETWORK = os.environ.get('NETWORK', 'mainnet')
BLOCKS_PREV = int(os.environ.get('BLOCKS_PREV', 10))

print(f'Using network {NETWORK} and contract {token_address}')

# TODO: write separate function to store in DynamoDB, then read this from DynamoDB
token_abi = os.environ.get('ABI')
if not token_abi:
    # Currently failing on kovan and ropsten - issue with py-etherscan-api?
    token_abi = get_contract_abi(token_address, etherscan_api_key=ETHERSCAN_API_KEY, network=NETWORK)
else:
    token_abi = json.loads(token_abi.replace('\\', ''))
token_interface = get_event_interface(token_abi)


def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    # try:
    #     ip = requests.get("http://checkip.amazonaws.com/")
    # except requests.RequestException as e:
    #     # Send some context about this error to Lambda Logs
    #     print(e)

    #     raise e

    # RPC interface - get token transfers in last 10 blocks
    current_block = get_current_block(infura_project_id=INFURA_PROJECT_ID, network=NETWORK)
    transfers = get_contract_events(
        token_address,
        from_block=current_block - BLOCKS_PREV,
        topics=[token_interface['Transfer']['topic']],
        infura_project_id=INFURA_PROJECT_ID,
        network=NETWORK
    )

    # Display
    transfer_events = [token_interface['Transfer']['decode'](t) for t in transfers]

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": transfer_events  # "hello world",
            # "location": ip.text.replace("\n", "")
        }),
    }
