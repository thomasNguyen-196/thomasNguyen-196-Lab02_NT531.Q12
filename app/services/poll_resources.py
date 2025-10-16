from datetime import datetime
from .auth import get_openstack_token
import requests
import json


def poll_openstack_resources(verbose=True, log_file=None):
    """
    Polls various OpenStack endpoints to gather resource information
    and saves it to a JSON file.
    """
    log_entries = []

    def _emit(message, console=None):
        timestamp = datetime.utcnow().isoformat()
        if console is None:
            console = verbose
        if console:
            print(message)
        if log_file:
            log_entries.append(f"{timestamp} {message}")

    try:
        if verbose:
            _emit("[poll] Attempting to get OpenStack token...", console=True)
        else:
            _emit("[poll] Updating cache from OpenStack...", console=True)

        token = get_openstack_token()
        headers = {"X-Auth-Token": token}

        if verbose:
            _emit("[poll] Token acquired successfully.", console=True)

        resources = {
            "flavors": "https://cloud-compute.uitiot.vn/v2.1/flavors/detail",
            "images": "https://cloud-compute.uitiot.vn/v2.1/images",
            "keypairs": "https://cloud-compute.uitiot.vn/v2.1/os-keypairs",
            "networks": "https://cloud-network.uitiot.vn/v2.0/networks",
            "servers": "https://cloud-compute.uitiot.vn/v2.1/servers/detail",
            "security_groups": "https://cloud-network.uitiot.vn/v2.0/security-groups",
            "routers": "https://cloud-network.uitiot.vn/v2.0/routers",
            "subnets": "https://cloud-network.uitiot.vn/v2.0/subnets",
            "floating_ips": "https://cloud-network.uitiot.vn/v2.0/floatingips",
            "ports": "https://cloud-network.uitiot.vn/v2.0/ports"
        }

        all_data = {}

        for resource_name, url in resources.items():
            _emit(f"[poll] Polling {resource_name} from {url}...")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                all_data[resource_name] = response.json()
                _emit(f"[poll] Successfully fetched {resource_name}.")
            else:
                _emit(f"[poll] Failed to fetch {resource_name}. Status: {response.status_code}, Body: {response.text}")
                all_data[resource_name] = None

        output_filename = "openstack_data.json"
        _emit(f"[poll] Writing all resource data to {output_filename}...", console=verbose)
        with open(output_filename, "w", encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        
        _emit("[poll] Polling complete. Data saved.", console=verbose)

    except Exception as e:
        _emit(f"[poll] An error occurred: {e}", console=True)

    finally:
        if log_file and log_entries:
            try:
                with open(log_file, "a", encoding="utf-8") as log_handle:
                    for line in log_entries:
                        log_handle.write(line + "\n")
                    log_handle.write("\n")
            except OSError as exc:
                print(f"[poll] Warning: Failed to write poll log ({exc}).")


if __name__ == "__main__":
    poll_openstack_resources()
