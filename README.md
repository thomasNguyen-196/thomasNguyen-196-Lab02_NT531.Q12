# OpenStack Provisioning GUI

## Overview
This project provides a CustomTkinter desktop application for managing
OpenStack resources. It authenticates against the UIT IoT Cloud Keystone
service, caches access tokens, polls common compute/network endpoints, and
offers guided flows for creating networks, subnets, and instances from a
single interface.

## Features
- Desktop GUI built with CustomTkinter, sized to surface all controls and live logs.
- Token-aware OpenStack authentication with on-disk caching and automatic reuse.
- One-click polling of flavors, images, key pairs, networks, servers, routers,
  subnets, floating IPs, ports, and security groups into `openstack_data.json`.
- Network workflow that provisions a subnet and, if desired, auto-creates a router
  and attaches the new subnet interface.
- Instance workflow with duplicate-name checks, plaintext cloud-init scripting
  (auto-base64 encoded), optional key pair injection, and floating IP selection
  plus automatic association after the VM is ready.
- Standalone helper scripts for polling resources or driving the API without
  the GUI.

## Requirements
- Python 3.11+ (3.13 recommended, matches the checked-in virtual environment).
- Access to the UIT IoT OpenStack environment and valid credentials.
- The packages listed in `requirements.txt` (install via `pip install -r
  requirements.txt`).

## Installation
```bash
# create and activate a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate  # Windows PowerShell

# install dependencies
pip install -r requirements.txt
```

## Environment Configuration
Create a `.env` file (copy `.env.example`) with the following keys:

- `ACCOUNT_ID`: Keystone user ID.
- `OPENSTACK_PROJECT_ID`: Project/tenant ID owning the resources.
- `ACCOUNT_PASSWORD_BASE64`: Base64-encoded login password.

Optional:
- `KEY_PAIR_NAME`: Base64-encoded Nova key pair name to associate with new
  instances.

To generate a Base64 string in PowerShell:
```powershell
python -c "import base64; print(base64.b64encode('your-secret'.encode()).decode())"
```
Paste the output into the corresponding `.env` entry.

## Running the App
```bash
python -m app.main
```
When the GUI opens, logs appear on the right-hand side. The app loads cached
OpenStack data (if available) or automatically polls the API on first launch.

## Usage
- **Refresh inventory**: Click the `Refresh` button in the GUI or use any resource-creation button; the app polls fresh data after each successful action. You can force a refresh from the terminal with `python -m app.services.poll_resources`.
- **Create a network**: Enter a name, corresponding subnet name, and CIDR, then click
  `Create`. Enable “Create router & attach subnet” to spin up a router and bind it
  to the freshly created subnet. Duplicate network names are prevented using cached data.
- **Create an instance**: Pick an image, flavor, security group, and network,
  provide an instance name, optionally paste a plaintext cloud-init script, and
  select a floating IP to bind after boot (or keep the “No floating IP” option).
  The app base64-encodes user data automatically before sending it to Nova.
- **Check for duplicates**: Background helpers in `app/utils/validate.py` prevent
  accidental reuse of network or server names.

## Command-Line Utilities
- `python -m app.services.poll_resources`: Polls all configured OpenStack endpoints and
  updates `openstack_data.json`.
- `python -m app.services.create_net_subnet`: Exposes the network/subnet creation helpers for
  scripting or testing.
- `python -m app.services.create_instance`: Provides the instance creation routine for use in
  automated flows.

## Data & Token Caching
- `token_cache.json`: Stores the most recent Keystone token and expiry. Delete
  this file to force re-authentication.
- `openstack_data.json`: Holds the latest snapshot of flavors, images, networks,
  routers, subnets, floating IPs, ports, and other resources. Regenerated via the
  GUI or `python -m app.services.poll_resources`.
- `poll_refresh.log`: Rolling log containing detailed poll output when the GUI
  refreshes inventory (console output stays concise).

## Project Structure
- `app/main.py`: Main GUI application entry point.
- `app/services/auth.py`: Keystone authentication and token caching logic.
- `app/services/poll_resources.py`: Resource polling utility used by the GUI and CLI.
- `app/services/create_net_subnet.py`: REST helpers for creating networks and subnets.
- `app/services/create_instance.py`: REST helper for provisioning new Nova instances.
- `app/services/router_fip.py`: Helpers for router creation, subnet attachment,
  port lookup, and floating IP association.
- `app/utils/validate.py`: Safeguards to detect duplicate resource names using cached
  data.

## Troubleshooting
- Ensure the `.env` file is present and populated before starting the app.
- Remove `token_cache.json` if credentials were rotated.
- Delete `openstack_data.json` if the cached inventory becomes stale or
  corrupted.
- All API calls use the UIT IoT OpenStack endpoints; confirm network
  connectivity if requests fail.
