from auth import get_openstack_token
import os
import requests
import json

# Lấy token
token = get_openstack_token()
# print("Your token:", token)

# Dùng token gọi API khác
compute_url = "https://cloud-compute.uitiot.vn/v2.1/servers"
headers = {"X-Auth-Token": os.getenv("OPENSTACK_TOKEN")}

response = requests.get(compute_url, headers=headers)
print(json.dumps(response.json(), indent=2))
