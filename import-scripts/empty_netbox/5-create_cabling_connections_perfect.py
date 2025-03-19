#!/usr/bin/env python3
import pynetbox
import requests
import colorama
from colorama import Fore, Style

# Initialize colorama for colored output
colorama.init()

# NetBox configuration
NETBOX_URL = "http://localhost"
NETBOX_TOKEN = ""


# Initialize NetBox API client with custom session
nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)

# Connection data from your table
CONNECTIONS = [
    {"node": "ceos-dc1-leaf1a", "interface": "Ethernet1", "peer_node": "ceos-dc1-spine1", "peer_interface": "Ethernet1"},
    {"node": "ceos-dc1-leaf1a", "interface": "Ethernet2", "peer_node": "ceos-dc1-spine2", "peer_interface": "Ethernet1"},
    {"node": "ceos-dc1-leaf1a", "interface": "Ethernet3", "peer_node": "ceos-dc1-leaf1b", "peer_interface": "Ethernet3"},
    {"node": "ceos-dc1-leaf1a", "interface": "Ethernet4", "peer_node": "ceos-dc1-leaf1b", "peer_interface": "Ethernet4"},
    {"node": "ceos-dc1-leaf1a", "interface": "Ethernet6", "peer_node": "ceos-dc1-leaf1c", "peer_interface": "Ethernet1"},
    {"node": "ceos-dc1-leaf1b", "interface": "Ethernet1", "peer_node": "ceos-dc1-spine1", "peer_interface": "Ethernet2"},
    {"node": "ceos-dc1-leaf1b", "interface": "Ethernet2", "peer_node": "ceos-dc1-spine2", "peer_interface": "Ethernet2"},
    {"node": "ceos-dc1-leaf1b", "interface": "Ethernet6", "peer_node": "ceos-dc1-leaf1c", "peer_interface": "Ethernet2"},
    {"node": "ceos-dc1-leaf2a", "interface": "Ethernet1", "peer_node": "ceos-dc1-spine1", "peer_interface": "Ethernet3"},
    {"node": "ceos-dc1-leaf2a", "interface": "Ethernet2", "peer_node": "ceos-dc1-spine2", "peer_interface": "Ethernet3"},
    {"node": "ceos-dc1-leaf2a", "interface": "Ethernet3", "peer_node": "ceos-dc1-leaf2b", "peer_interface": "Ethernet3"},
    {"node": "ceos-dc1-leaf2a", "interface": "Ethernet4", "peer_node": "ceos-dc1-leaf2b", "peer_interface": "Ethernet4"},
    {"node": "ceos-dc1-leaf2a", "interface": "Ethernet6", "peer_node": "ceos-dc1-leaf2c", "peer_interface": "Ethernet1"},
    {"node": "ceos-dc1-leaf2b", "interface": "Ethernet1", "peer_node": "ceos-dc1-spine1", "peer_interface": "Ethernet4"},
    {"node": "ceos-dc1-leaf2b", "interface": "Ethernet2", "peer_node": "ceos-dc1-spine2", "peer_interface": "Ethernet4"},
    {"node": "ceos-dc1-leaf2b", "interface": "Ethernet6", "peer_node": "ceos-dc1-leaf2c", "peer_interface": "Ethernet2"},
    {"node": "ceos-dc1-leaf3a", "interface": "Ethernet1", "peer_node": "ceos-dc1-spine1", "peer_interface": "Ethernet5"},
    {"node": "ceos-dc1-leaf3a", "interface": "Ethernet2", "peer_node": "ceos-dc1-spine2", "peer_interface": "Ethernet5"},
    {"node": "ceos-dc1-leaf3a", "interface": "Ethernet3", "peer_node": "ceos-dc1-leaf3b", "peer_interface": "Ethernet3"},
    {"node": "ceos-dc1-leaf3a", "interface": "Ethernet4", "peer_node": "ceos-dc1-leaf3b", "peer_interface": "Ethernet4"},
    {"node": "ceos-dc1-leaf3b", "interface": "Ethernet1", "peer_node": "ceos-dc1-spine1", "peer_interface": "Ethernet6"},
    {"node": "ceos-dc1-leaf3b", "interface": "Ethernet2", "peer_node": "ceos-dc1-spine2", "peer_interface": "Ethernet6"},
]

def print_regular(message):
    print(f"{Fore.WHITE}{message}{Style.RESET_ALL}")

def print_warning(message):
    print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")

def print_error(message):
    print(f"{Fore.RED}{message}{Style.RESET_ALL}")

def get_existing_interface(device_name, interface_name):
    """Retrieve an existing interface from a device."""
    device = nb.dcim.devices.get(name=device_name)
    if not device:
        print_error(f"Device {device_name} not found in NetBox. Skipping.")
        return None
    interface = nb.dcim.interfaces.get(device_id=device.id, name=interface_name)
    if not interface:
        print_error(f"Interface {interface_name} not found on {device_name}. Skipping.")
        return None
    return interface

def create_cable_connection(interface_a, interface_b):
    """Create a cable connection between two existing interfaces if it doesn’t exist."""
    # Check if a cable already exists between these interfaces
    existing_cables = nb.dcim.cables.filter(
        termination_a_type="dcim.interface", termination_a_id=interface_a.id,
        termination_b_type="dcim.interface", termination_b_id=interface_b.id
    ) or nb.dcim.cables.filter(
        termination_a_type="dcim.interface", termination_a_id=interface_b.id,
        termination_b_type="dcim.interface", termination_b_id=interface_a.id
    )
    if not list(existing_cables):
        try:
            nb.dcim.cables.create(
                a_terminations=[{"object_type": "dcim.interface", "object_id": interface_a.id}],
                b_terminations=[{"object_type": "dcim.interface", "object_id": interface_b.id}],
                type="cat6",  # Adjust cable type as needed (e.g., "mmf" for fiber)
                status="connected"
            )
            print_regular(f"Created cable between {interface_a.device.name}:{interface_a.name} and {interface_b.device.name}:{interface_b.name}")
        except pynetbox.core.query.RequestError as e:
            print_error(f"Failed to create cable between {interface_a.device.name}:{interface_a.name} and {interface_b.device.name}:{interface_b.name}: {e}")
    else:
        print_warning(f"Cable already exists between {interface_a.device.name}:{interface_a.name} and {interface_b.device.name}:{interface_b.name}. Skipping.")

def configure_cables():
    """Configure cables in NetBox based on CONNECTIONS."""
    print_regular("Starting configuration of cables in NetBox...")

    for conn in CONNECTIONS:
        # Get existing interfaces
        interface = get_existing_interface(conn["node"], conn["interface"])
        peer_interface = get_existing_interface(conn["peer_node"], conn["peer_interface"])
        if not interface or not peer_interface:
            continue

        # Create cable connection
        create_cable_connection(interface, peer_interface)

    print_regular("Cable configuration process completed.")

def main():
    configure_cables()

if __name__ == "__main__":
    main()
