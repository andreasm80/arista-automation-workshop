import requests
import json

# NetBox API configuration - adjust these as needed
NETBOX_URL = "http://localhost:8080"  # Your NetBox instance URL
API_TOKEN = "YOUR_API_TOKEN_HERE"     # Replace with your actual API token

# Headers for API requests
headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def setup_initial_data():
    """Setup initial data including roles, manufacturer, device type, and platform"""
    
    # 1. Add device roles
    roles = [
        {"name": "l3leaf", "slug": "l3leaf", "description": "Layer 3 Leaf"},
        {"name": "l2leaf", "slug": "l2leaf", "description": "Layer 2 Leaf"},
        {"name": "spine", "slug": "spine", "description": "Spine"}
    ]
    
    for role in roles:
        response = requests.post(
            f"{NETBOX_URL}/api/dcim/device-roles/",
            headers=headers,
            json=role
        )
        if response.status_code == 201:
            print(f"Created role: {role['name']}")
        elif response.status_code == 409:  # Already exists
            print(f"Role {role['name']} already exists")
        else:
            print(f"Failed to create role {role['name']}: {response.text}")

    # 2. Add Manufacturer
    manufacturer = {
        "name": "Arista",
        "slug": "arista",
        "description": "Arista Networks"
    }
    response = requests.post(
        f"{NETBOX_URL}/api/dcim/manufacturers/",
        headers=headers,
        json=manufacturer
    )
    if response.status_code == 201:
        print("Created manufacturer: Arista")
    elif response.status_code == 409:
        print("Manufacturer Arista already exists")

    # 3. Add Device Type
    device_type = {
        "manufacturer": {"name": "Arista"},
        "model": "cEOSLab",
        "slug": "ceoslab",
        "description": "Arista cEOS Lab Device"
    }
    response = requests.post(
        f"{NETBOX_URL}/api/dcim/device-types/",
        headers=headers,
        json=device_type
    )
    if response.status_code == 201:
        print("Created device type: cEOSLab")
    elif response.status_code == 409:
        print("Device type cEOSLab already exists")

    # 4. Add Platform
    platform = {
        "name": "eos",
        "slug": "eos",
        "description": "Arista EOS"
    }
    response = requests.post(
        f"{NETBOX_URL}/api/dcim/platforms/",
        headers=headers,
        json=platform
    )
    if response.status_code == 201:
        print("Created platform: eos")
    elif response.status_code == 409:
        print("Platform eos already exists")

def get_resource_id(endpoint, filter_key, filter_value):
    """Get the ID of a resource based on a filter"""
    response = requests.get(
        f"{NETBOX_URL}/api/dcim/{endpoint}/",
        headers=headers,
        params={filter_key: filter_value}
    )
    if response.status_code == 200 and response.json()["results"]:
        return response.json()["results"][0]["id"]
    return None

def create_device(name, role_name):
    """Create a device with the given name and role"""
    
    # Get required IDs
    role_id = get_resource_id("device-roles", "slug", role_name)
    device_type_id = get_resource_id("device-types", "slug", "ceoslab")
    platform_id = get_resource_id("platforms", "slug", "eos")
    site_id = get_resource_id("sites", "slug", "dc1")  # Assuming site from template

    if not all([role_id, device_type_id, platform_id, site_id]):
        print(f"Error: Could not find all required resources for {name}")
        return

    # Device data based on template
    device_data = {
        "name": name,
        "device_type": device_type_id,
        "role": role_id,
        "platform": platform_id,
        "site": site_id,
        "status": "active",
        "description": ""
    }

    response = requests.post(
        f"{NETBOX_URL}/api/dcim/devices/",
        headers=headers,
        json=device_data
    )
    
    if response.status_code == 201:
        print(f"Successfully created device: {name}")
    else:
        print(f"Failed to create device {name}: {response.text}")

def main():
    # Setup initial data first
    setup_initial_data()
    
    print("\nEnter device information (press Enter without a name to finish):")
    
    valid_roles = ["l3leaf", "l2leaf", "spine"]
    
    while True:
        name = input("Enter device name (or press Enter to finish): ").strip()
        if not name:
            break
            
        while True:
            role = input("Enter device role (l3leaf/l2leaf/spine): ").strip().lower()
            if role in valid_roles:
                break
            print("Invalid role. Please use l3leaf, l2leaf, or spine.")
        
        create_device(name, role)

if __name__ == "__main__":
    main()
