import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

NETWORK_BASE_URL = "https://cloud-network.uitiot.vn/v2.0"


def _network_headers(token):
    return {
        "X-Auth-Token": token,
        "Content-Type": "application/json",
    }


def create_router(token, router_name, external_network_id=None, project_id=None):
    """
    Create a Neutron router attached to the external network.
    """
    project_id = project_id or os.getenv("OPENSTACK_PROJECT_ID")
    if not project_id:
        raise ValueError("Missing OPENSTACK_PROJECT_ID in environment.")

    external_network_id = (
        external_network_id
        or os.getenv("OPENSTACK_EXTERNAL_NETWORK_ID")
        or "c3455e8f-ea16-4f5d-ad5e-5c4292015a0d"
    )

    payload = {
        "router": {
            "name": router_name,
            "project_id": project_id,
            "external_gateway_info": {
                "network_id": external_network_id,
            },
            "admin_state_up": True,
        }
    }

    url = f"{NETWORK_BASE_URL}/routers"
    try:
        response = requests.post(url, headers=_network_headers(token), data=json.dumps(payload))
        if response.status_code == 201:
            router = response.json().get("router", {})
            router_id = router.get("id")
            print(f"[router] Created router '{router_name}' (ID: {router_id}).")
            return router_id

        print(f"[router] Failed to create router '{router_name}'. Status: {response.status_code}")
        print(f"[router] Response: {response.text}")
    except requests.RequestException as exc:
        print(f"[router] Exception during router creation: {exc}")
    return None


def add_subnet_interface(token, router_id, subnet_id):
    """
    Attach a subnet interface to an existing router.
    """
    url = f"{NETWORK_BASE_URL}/routers/{router_id}/add_router_interface"
    payload = {"subnet_id": subnet_id}

    try:
        response = requests.put(url, headers=_network_headers(token), data=json.dumps(payload))
        if response.status_code in (200, 201):
            print(f"[router] Attached subnet {subnet_id} to router {router_id}.")
            return response.json()

        print(
            f"[router] Failed to attach subnet {subnet_id} to router {router_id}. "
            f"Status: {response.status_code}"
        )
        print(f"[router] Response: {response.text}")
    except requests.RequestException as exc:
        print(f"[router] Exception during interface attachment: {exc}")
    return None


def associate_floating_ip(token, floating_ip_id, port_id):
    """
    Associate a floating IP with a specific Neutron port.
    """
    url = f"{NETWORK_BASE_URL}/floatingips/{floating_ip_id}"
    payload = {"floatingip": {"port_id": port_id}}

    try:
        response = requests.put(url, headers=_network_headers(token), data=json.dumps(payload))
        if response.status_code == 200:
            print(f"[floating-ip] Associated floating IP {floating_ip_id} with port {port_id}.")
            return response.json()

        print(
            f"[floating-ip] Failed to associate floating IP {floating_ip_id}. "
            f"Status: {response.status_code}"
        )
        print(f"[floating-ip] Response: {response.text}")
    except requests.RequestException as exc:
        print(f"[floating-ip] Exception during association: {exc}")
    return None


def get_ports_for_device(token, device_id):
    """
    Return Neutron ports that belong to a specific device (instance).
    """
    url = f"{NETWORK_BASE_URL}/ports"
    params = {"device_id": device_id}

    try:
        response = requests.get(url, headers={"X-Auth-Token": token}, params=params)
        if response.status_code == 200:
            ports = response.json().get("ports", [])
            print(f"[ports] Fetched {len(ports)} port(s) for device {device_id}.")
            return ports

        print(f"[ports] Failed to fetch ports for device {device_id}. Status: {response.status_code}")
        print(f"[ports] Response: {response.text}")
    except requests.RequestException as exc:
        print(f"[ports] Exception while fetching ports: {exc}")
    return []
