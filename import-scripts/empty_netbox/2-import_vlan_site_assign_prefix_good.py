import pynetbox
import yaml
import os
import requests
import time
import colorama
from colorama import Fore, Style

# Initialize colorama for colored output
colorama.init()

# NetBox configuration
NETBOX_URL = "http://localhost"
NETBOX_TOKEN = "3388e839465c444ddce04c69a9968fd63473a251"
CONFIG_DIR = "../intended/structured_configs"


# Initialize NetBox API client with custom session
nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)

def print_regular(message):
    print(f"{Fore.WHITE}{message}{Style.RESET_ALL}")

def print_warning(message):
    print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")

def print_error(message):
    print(f"{Fore.RED}{message}{Style.RESET_ALL}")

def ip_to_network_prefix(ip_with_mask):
    """Convert an IP with mask to its network prefix."""
    try:
        import ipaddress
        network = ipaddress.ip_network(ip_with_mask, strict=False)
        return str(network)
    except ValueError as e:
        print_warning(f"Invalid IP/mask {ip_with_mask}: {e}")
        return None

def collect_vlans_and_prefixes():
    """Collect VLANs and their associated prefixes from all YAML files."""
    vlans = {}

    for filename in os.listdir(CONFIG_DIR):
        if filename.endswith((".yaml", ".yml")):
            yaml_file = os.path.join(CONFIG_DIR, filename)
            with open(yaml_file, "r") as f:
                try:
                    config = yaml.safe_load(f)
                    # Collect VLANs from the 'vlans' section
                    for vlan in config.get("vlans", []):
                        vlan_id = vlan.get("id")
                        if vlan_id:
                            vlan_name = vlan.get("name", f"VLAN{vlan_id}")
                            tenant_name = vlan.get("tenant", "system")
                            if vlan_id not in vlans:
                                vlans[vlan_id] = {
                                    "name": vlan_name,
                                    "tenant": tenant_name,
                                    "prefixes": {}
                                }
                            else:
                                # Update name or tenant if different (prioritize vlan_interfaces later)
                                vlans[vlan_id]["name"] = vlan_name
                                vlans[vlan_id]["tenant"] = tenant_name

                    # Link VLANs to prefixes from vlan_interfaces
                    for vlan_intf in config.get("vlan_interfaces", []):
                        vlan_name = vlan_intf["name"]  # e.g., Vlan11
                        if vlan_name.startswith("Vlan"):
                            try:
                                vlan_id = int(vlan_name.replace("Vlan", ""))
                                ip_addr = vlan_intf.get("ip_address") or vlan_intf.get("ip_address_virtual")
                                if ip_addr:
                                    network_prefix = ip_to_network_prefix(ip_addr)
                                    if network_prefix:
                                        vrf_name = vlan_intf.get("vrf", "vrf-ceos-dc1-prod-underlay")
                                        tenant_name = vlan_intf.get("tenant", vlans.get(vlan_id, {}).get("tenant", "system"))
                                        if vlan_id not in vlans:
                                            vlans[vlan_id] = {
                                                "name": vlan_intf.get("description", f"VLAN{vlan_id}"),
                                                "tenant": tenant_name,
                                                "prefixes": {}
                                            }
                                        vlans[vlan_id]["tenant"] = tenant_name  # Update tenant from vlan_interfaces
                                        if vrf_name not in vlans[vlan_id]["prefixes"]:
                                            vlans[vlan_id]["prefixes"][vrf_name] = set()
                                        vlans[vlan_id]["prefixes"][vrf_name].add(network_prefix)
                            except ValueError:
                                print_warning(f"Invalid VLAN name format in {yaml_file}: {vlan_name}")
                                continue

                except yaml.YAMLError as e:
                    print_error(f"Error parsing YAML file {yaml_file}: {e}")

    return vlans

def get_vrf_id(vrf_name):
    """Get the VRF ID from NetBox by its name."""
    vrf = nb.ipam.vrfs.get(name=vrf_name)
    if vrf:
        return vrf.id
    print_warning(f"VRF {vrf_name} not found in NetBox.")
    return None

def get_or_create_site(site_name, site_slug):
    """Get or create a site with the given name and slug."""
    site = nb.dcim.sites.get(slug=site_slug)
    if not site:
        try:
            site = nb.dcim.sites.create(
                name=site_name,
                slug=site_slug,
                status="active"
            )
            print_regular(f"Created site '{site_name}' (ID: {site.id})")
        except pynetbox.core.query.RequestError as e:
            print_error(f"Failed to create site '{site_name}': {e}")
            return None
    return site

def create_vlans_with_prefixes(vlans):
    """Create VLANs in NetBox and assign prefixes, placing them in site DC1."""
    # Get or create the DC1 site
    site = get_or_create_site("DC1", "dc1")
    if not site:
        print_error("Failed to get or create site DC1. Aborting.")
        return

    for vlan_id, vlan_data in vlans.items():
        tenant_id = None
        prefix_to_assign = None
        vrf_id = None

        # Check all prefixes in all VRFs for this VLAN
        for vrf_name, prefix_set in vlan_data["prefixes"].items():
            vrf_id = get_vrf_id(vrf_name)
            if not vrf_id:
                continue  # Skip if VRF not found

            for prefix in prefix_set:
                # Look up the prefix in NetBox with the correct VRF ID
                existing_prefix = nb.ipam.prefixes.get(
                    prefix=prefix,
                    vrf_id=vrf_id
                )
                if existing_prefix:
                    tenant_id = existing_prefix.tenant.id if existing_prefix.tenant else None
                    prefix_to_assign = existing_prefix
                    break  # Use the first matching prefix's tenant info
            if tenant_id:  # Break outer loop if we found a tenant
                break

        # If no prefix is found, use the tenant specified in the YAML (default to 'system')
        if not tenant_id:
            tenant_name = vlan_data["tenant"]
            tenant = nb.tenancy.tenants.get(slug=tenant_name.lower().replace(" ", "-"))
            if tenant:
                tenant_id = tenant.id
            else:
                print_warning(f"Tenant {tenant_name} not found in NetBox for VLAN {vlan_id}. Skipping.")
                continue

        # Check if VLAN already exists
        vlan = nb.ipam.vlans.get(vid=vlan_id, tenant_id=tenant_id)
        if not vlan:
            try:
                vlan = nb.ipam.vlans.create(
                    vid=vlan_id,
                    name=vlan_data["name"],
                    tenant=tenant_id,
                    site=site.id,
                    status="active"
                )
                print_regular(f"Created VLAN {vlan_id} ({vlan_data['name']}) with tenant ID {tenant_id} in site 'DC1' (VLAN ID: {vlan.id})")
            except pynetbox.core.query.RequestError as e:
                print_error(f"Failed to create VLAN {vlan_id}: {e}")
                continue
        else:
            # Update VLAN if name or site differs
            needs_update = False
            if vlan.name != vlan_data["name"]:
                vlan.name = vlan_data["name"]
                needs_update = True
            if vlan.site != site.id:
                vlan.site = site.id
                needs_update = True
            if needs_update:
                vlan.save()
                print_regular(f"Updated VLAN {vlan_id} ({vlan_data['name']}) to site 'DC1'")
            else:
                print_regular(f"VLAN {vlan_id} already exists with correct tenant and site")

        # Assign the prefix to the VLAN if applicable
        if prefix_to_assign:
            if not prefix_to_assign.vlan or prefix_to_assign.vlan.id != vlan.id:
                prefix_to_assign.vlan = vlan.id
                try:
                    prefix_to_assign.save()
                    print_regular(f"Assigned prefix {prefix_to_assign.prefix} (VRF: {vrf_name}) to VLAN {vlan_id}")
                except pynetbox.core.query.RequestError as e:
                    print_error(f"Failed to assign prefix {prefix_to_assign.prefix} to VLAN {vlan_id}: {e}")
            else:
                print_regular(f"Prefix {prefix_to_assign.prefix} already assigned to VLAN {vlan_id}")

def main():
    if not os.path.exists(CONFIG_DIR):
        print_warning(f"Config directory {CONFIG_DIR} not found.")
        return

    print_regular("Collecting VLANs and prefixes from YAML files...")
    vlans = collect_vlans_and_prefixes()

    print_regular("Creating VLANs and assigning prefixes in NetBox...")
    create_vlans_with_prefixes(vlans)

    print_regular("VLAN creation process completed.")

if __name__ == "__main__":
    main()
