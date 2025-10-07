import requests
import json
from auth import get_openstack_token


def create_network(token, network_name):
    """
    Sends an API request to create a new network in OpenStack.

    Args:
        token (str): The OpenStack authentication token.
        network_name (str): The desired name for the new network.

    Returns:
        str: The ID of the newly created network, or None on failure.
    """
    print(f"--> Attempting to create network: {network_name}")
    network_endpoint = "https://cloud-network.uitiot.vn/v2.0/networks"
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }
    payload = {
        "network": {
            "name": network_name,
            "admin_state_up": True
        }
    }

    try:
        response = requests.post(network_endpoint, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 201:
            print(f"--> Success! Network '{network_name}' created.")
            network_data = response.json()
            return network_data.get("network", {}).get("id")
        else:
            print(f"--> Error creating network. Status: {response.status_code}")
            print(f"--> Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"--> An exception occurred during the API request: {e}")
        return None

def create_subnet(token, subnet_name, network_id, cidr):
    """
    Sends an API request to create a new subnet in OpenStack.

    Args:
        token (str): The OpenStack authentication token.
        subnet_name (str): The desired name for the new subnet.
        network_id (str): The ID of the parent network.
        cidr (str): The CIDR for the new subnet (e.g., "192.168.1.0/24").

    Returns:
        str: The ID of the newly created subnet, or None on failure.
    """
    print(f"--> Attempting to create subnet: {subnet_name}")
    subnet_endpoint = "https://cloud-network.uitiot.vn/v2.0/subnets"
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }
    payload = {
        "subnet": {
            "name": subnet_name,
            "network_id": network_id,
            "ip_version": 4,
            "cidr": cidr,
            "enable_dhcp": True
        }
    }

    try:
        response = requests.post(subnet_endpoint, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 201:
            print(f"--> Success! Subnet '{subnet_name}' created.")
            subnet_data = response.json()
            return subnet_data.get("subnet", {}).get("id")
        else:
            print(f"--> Error creating subnet. Status: {response.status_code}")
            print(f"--> Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"--> An exception occurred during the API request: {e}")
        return None
