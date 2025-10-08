from .auth import get_openstack_token
import requests
import json

def poll_openstack_resources():
    """
    Polls various OpenStack endpoints to gather resource information
    and saves it to a JSON file.
    """
    try:
        print("[poll] Attempting to get OpenStack token...")
        token = get_openstack_token()
        headers = {"X-Auth-Token": token}
        print("[poll] Token acquired successfully.")

        resources = {
            "flavors": "https://cloud-compute.uitiot.vn/v2.1/flavors/detail",
            "images": "https://cloud-compute.uitiot.vn/v2.1/images",
            "keypairs": "https://cloud-compute.uitiot.vn/v2.1/os-keypairs",
            "networks": "https://cloud-network.uitiot.vn/v2.0/networks",
            "servers": "https://cloud-compute.uitiot.vn/v2.1/servers",
            "security_groups": "https://cloud-network.uitiot.vn/v2.0/security-groups"
        }

        all_data = {}

        for resource_name, url in resources.items():
            print(f"[poll] Polling {resource_name} from {url}...")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                all_data[resource_name] = response.json()
                print(f"[poll] Successfully fetched {resource_name}.")
            else:
                print(f"[poll] Failed to fetch {resource_name}. Status: {response.status_code}, Body: {response.text}")
                all_data[resource_name] = None

        output_filename = "openstack_data.json"
        print(f"[poll] Writing all resource data to {output_filename}...")
        with open(output_filename, "w", encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        
        print("[poll] Polling complete. Data saved.")

    except Exception as e:
        print(f"[poll] An error occurred: {e}")

if __name__ == "__main__":
    poll_openstack_resources()
