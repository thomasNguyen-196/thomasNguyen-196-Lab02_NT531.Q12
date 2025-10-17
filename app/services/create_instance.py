import requests
import json
import os
import base64

def create_instance(token, instance_name, image_id, flavor_id, network_id, user_data=None):
    """
    Sends an API request to create a new instance (virtual machine) in OpenStack.

    Args:
        token (str): The OpenStack authentication token.
        instance_name (str): The desired name for the new instance.
        image_id (str): The ID of the image to use for the instance.
        flavor_id (str): The ID of the flavor to use for the instance.
        network_id (str): The ID of the network to attach the instance to.
        user_data (str, optional): Base64-encoded user data script to run on instance boot.
    Returns:
        str: The ID of the newly created instance, or None on failure.
    """
    print(f"--> Attempting to create instance: {instance_name}")
    instance_endpoint = "https://cloud-compute.uitiot.vn/v2.1/servers"
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }

    # Base payload structure
    payload = {
        "server": {
            "name": instance_name,
            "imageRef": image_id,
            "flavorRef": flavor_id,
            "networks": [{"uuid": network_id}],
            "security_groups" : [
                {
                    "name" : "default"
                }
            ]
        }
    }

    if user_data:
        encoded_user_data = base64.b64encode(user_data.encode('utf-8')).decode('utf-8')

        payload["server"]["user_data"] = encoded_user_data

        print("--> Added user_data to payload (base64 encoded).")
    
    # Get key pair name from environment variable if available
    key_name = os.getenv("KEY_PAIR_NAME_BASE64")
    if key_name:
        payload["server"]["key_name"] = base64.b64decode(key_name).decode('utf-8')
        print(f"--> Added key_name '{payload['server']['key_name']}' to payload.")

    try:
        response = requests.post(instance_endpoint, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 202:
            print(f"--> Success! Instance '{instance_name}' created.")
            instance_data = response.json()
            return instance_data.get("server", {}).get("id")
        else:
            print(f"--> Error creating instance. Status: {response.status_code}")
            print(f"--> Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"--> An exception occurred during the API request: {e}")
        return None