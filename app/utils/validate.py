import json
import os

DATA_FILE = "openstack_data.json"

def _load_data():
    """Loads JSON data from cache, returns empty dict if not found or invalid."""
    if not os.path.exists(DATA_FILE):
        print(f"Warning: {DATA_FILE} not found.")
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse {DATA_FILE}: {e}")
        return {}

def is_network_duplicate(name):
    """Check if a network with the same name already exists."""
    data = _load_data()
    networks = data.get("networks", {}).get("networks", [])
    return any(net.get("name") == name for net in networks)

def is_instance_duplicate(name):
    """Check if an instance with the same name already exists."""
    data = _load_data()
    servers = data.get("servers", {}).get("servers", [])
    return any(vm.get("name") == name for vm in servers)


def get_available_floating_ips():
    """Return floating IP objects that are not currently associated with any port."""
    data = _load_data()
    floating_ips = data.get("floating_ips", {}).get("floatingips", [])
    return [ip for ip in floating_ips if not ip.get("port_id")]


def get_port_id_by_device(device_id):
    """Return the first Neutron port ID that matches the supplied device (instance) ID."""
    if not device_id:
        return None

    data = _load_data()
    ports = data.get("ports", {}).get("ports", [])
    for port in ports:
        if port.get("device_id") == device_id:
            return port.get("id")
    return None
