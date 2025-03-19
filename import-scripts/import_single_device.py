import pynetbox
import yaml
import os
import requests
import time
import colorama
import ipaddress
from colorama import Fore, Style

# Initialize colorama for colored output
colorama.init()

# NetBox configuration
NETBOX_URL = "http://localhost"
NETBOX_TOKEN = ""
CONFIG_DIR = "../intended/structured_configs"
DEFAULT_MTU = 1500


# Initialize NetBox API client with custom session
nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)

def print_regular(message):
    print(f"{Fore.WHITE}{message}{Style.RESET_ALL}")

def print_warning(message):
    print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")

def print_error(message):
    print(f"{Fore.RED}{message}{Style.RESET_ALL}")

def get_or_create_device_type(device_type_name):
    device_type = nb.dcim.device_types.get(slug=device_type_name.lower().replace(" ", "-"))
    if not device_type:
        device_type = nb.dcim.device_types.create(
            manufacturer=1,
            model=device_type_name,
            slug=device_type_name.lower().replace(" ", "-")
        )
    return device_type

def get_or_create_role(role_name):
    role = nb.dcim.device_roles.get(slug=role_name.lower().replace(" ", "-"))
    if not role:
        role = nb.dcim.device_roles.create(
            name=role_name,
            slug=role_name.lower().replace(" ", "-"),
            color="blue"
        )
    return role

def get_or_create_tenant(tenant_name, slug, group_name="ceos-dc1-production"):
    tenant_group = nb.tenancy.tenant_groups.get(slug=group_name.lower().replace(" ", "-"))
    if not tenant_group:
        tenant_group = nb.tenancy.tenant_groups.create(
            name=group_name,
            slug=group_name.lower().replace(" ", "-")
        )
    tenant = nb.tenancy.tenants.get(slug=slug)
    if not tenant:
        tenant = nb.tenancy.tenants.create(
            name=tenant_name,
            slug=slug,
            group=tenant_group.id
        )
    elif tenant.group.id != tenant_group.id:
        tenant.group = tenant_group.id
        tenant.save()
    return tenant

def get_or_create_vrf(vrf_name, tenant_name, tenant_slug):
    tenant = get_or_create_tenant(tenant_name, tenant_slug)
    vrf = nb.ipam.vrfs.get(name=vrf_name)
    if not vrf:
        vrf = nb.ipam.vrfs.create(
            name=vrf_name,
            tenant=tenant.id
        )
        print_regular(f"Created VRF {vrf_name} with tenant {tenant_name}")
    else:
        if vrf.tenant.id != tenant.id:
            vrf.tenant = tenant.id
            vrf.save()
            print_regular(f"Updated VRF {vrf_name} with tenant {tenant_name}")
    return vrf

def ip_to_network_prefix(ip_with_mask):
    """Convert an IP with mask to its network prefix."""
    try:
        network = ipaddress.ip_network(ip_with_mask, strict=False)
        return str(network)
    except ValueError as e:
        print_warning(f"Invalid IP/mask {ip_with_mask}: {e}")
        return None

def collect_ip_usage_and_prefixes(device_name):
    """Collect IPs for Anycast detection and prefixes for creation for a specific device."""
    ip_usage = {}
    prefixes = {}

    yaml_file = os.path.join(CONFIG_DIR, f"{device_name}.yml")
    if not os.path.exists(yaml_file):
        yaml_file = os.path.join(CONFIG_DIR, f"{device_name}.yaml")
    if not os.path.exists(yaml_file):
        print_error(f"No configuration file found for {device_name} in {CONFIG_DIR}")
        return {}, {}

    with open(yaml_file, "r") as f:
        try:
            config = yaml.safe_load(f)
            hostname = config.get("hostname", device_name)
            for intf_type, intfs in [
                ("management_interfaces", config.get("management_interfaces", [])),
                ("ethernet_interfaces", config.get("ethernet_interfaces", [])),
                ("vlan_interfaces", config.get("vlan_interfaces", [])),
                ("loopback_interfaces", config.get("loopback_interfaces", [])),
                ("port_channel_interfaces", config.get("port_channel_interfaces", []))
            ]:
                for intf_data in intfs:
                    ip_addr = intf_data.get("ip_address") or intf_data.get("ip_address_virtual")
                    if ip_addr:
                        key = (hostname, intf_type, intf_data["name"])
                        if ip_addr not in ip_usage:
                            ip_usage[ip_addr] = []
                        ip_usage[ip_addr].append(key)
                        vrf_name = intf_data.get("vrf", "vrf-ceos-dc1-prod-underlay")
                        network_prefix = ip_to_network_prefix(ip_addr)
                        if network_prefix:
                            if vrf_name not in prefixes:
                                prefixes[vrf_name] = set()
                            prefixes[vrf_name].add(network_prefix)

            for prefix_list in config.get("prefix_lists", []):
                for seq in prefix_list.get("sequence_numbers", []):
                    action = seq.get("action", "")
                    if "permit" in action:
                        parts = action.split()
                        prefix = parts[1] if len(parts) > 1 else None
                        if prefix:
                            network_prefix = ip_to_network_prefix(prefix)
                            if network_prefix:
                                vrf_name = "vrf-ceos-dc1-prod-underlay"
                                if vrf_name not in prefixes:
                                    prefixes[vrf_name] = set()
                                prefixes[vrf_name].add(network_prefix)

            for route in config.get("static_routes", []):
                prefix = route.get("destination_address_prefix")
                if prefix and prefix != "0.0.0.0/0":
                    network_prefix = ip_to_network_prefix(prefix)
                    if network_prefix:
                        vrf_name = route.get("vrf", "vrf-ceos-dc1-prod-underlay")
                        if vrf_name not in prefixes:
                            prefixes[vrf_name] = set()
                        prefixes[vrf_name].add(network_prefix)

        except yaml.YAMLError as e:
            print_error(f"Error parsing YAML file {yaml_file}: {e}")
            return {}, {}

    # Check all devices to identify Anycast IPs
    for filename in os.listdir(CONFIG_DIR):
        if filename.endswith((".yaml", ".yml")) and filename != os.path.basename(yaml_file):
            other_yaml_file = os.path.join(CONFIG_DIR, filename)
            with open(other_yaml_file, "r") as f:
                try:
                    config = yaml.safe_load(f)
                    for intf_type, intfs in [
                        ("management_interfaces", config.get("management_interfaces", [])),
                        ("ethernet_interfaces", config.get("ethernet_interfaces", [])),
                        ("vlan_interfaces", config.get("vlan_interfaces", [])),
                        ("loopback_interfaces", config.get("loopback_interfaces", [])),
                        ("port_channel_interfaces", config.get("port_channel_interfaces", []))
                    ]:
                        for intf_data in intfs:
                            ip_addr = intf_data.get("ip_address") or intf_data.get("ip_address_virtual")
                            if ip_addr and ip_addr in ip_usage:
                                key = (config.get("hostname", "unknown"), intf_type, intf_data["name"])
                                ip_usage[ip_addr].append(key)
                except yaml.YAMLError as e:
                    print_error(f"Error parsing YAML file {other_yaml_file}: {e}")

    anycast_ips = {ip: usages for ip, usages in ip_usage.items() if len(usages) > 1}
    print_regular(f"Detected Anycast IPs for {device_name}: {list(anycast_ips.keys())}")
    return anycast_ips, prefixes

def create_prefixes(prefixes, vrfs):
    """Create prefixes in NetBox under the correct VRFs."""
    for vrf_name, prefix_set in prefixes.items():
        vrf = vrfs.get(vrf_name, vrfs["vrf-ceos-dc1-prod-underlay"])
        tenant = vrf.tenant
        for prefix in prefix_set:
            existing_prefix = nb.ipam.prefixes.get(prefix=prefix, vrf_id=vrf.id)
            if not existing_prefix:
                try:
                    new_prefix = nb.ipam.prefixes.create(
                        prefix=prefix,
                        vrf=vrf.id,
                        tenant=tenant.id,
                        status="active"
                    )
                    print_regular(f"Created prefix {prefix} in VRF {vrf.name} with tenant {tenant.name} (Prefix ID: {new_prefix.id})")
                except pynetbox.core.query.RequestError as e:
                    print_error(f"Failed to create prefix {prefix} in VRF {vrf.name}: {e}")
            else:
                print_regular(f"Prefix {prefix} already exists in VRF {vrf.name}")

def update_interface(device, intf_data, intf_type, anycast_ips, vrfs):
    """Update or create an interface and its IP, ensuring proper VRF and Anycast handling."""
    intf_name = intf_data["name"]
    interface = nb.dcim.interfaces.get(device_id=device.id, name=intf_name)
    if not interface:
        print_regular(f"Creating new {intf_type.capitalize()} interface {intf_name} for {device.name}")
        interface_type = "100gbase-x-qsfp28" if intf_type == "ethernet" else "1000base-t" if intf_type == "management" else "virtual" if intf_type in ["vlan", "loopback"] else "lag"
        interface = nb.dcim.interfaces.create(
            device=device.id,
            name=intf_name,
            type=interface_type,
            description=intf_data.get("description", ""),
            enabled=not intf_data.get("shutdown", False)
        )
        time.sleep(1)
    else:
        interface.description = intf_data.get("description", interface.description)
        interface.enabled = not intf_data.get("shutdown", False)
        interface.save()

    mtu = intf_data.get("mtu", DEFAULT_MTU)
    if interface.mtu != mtu:
        interface.mtu = mtu
        interface.save()
        print_regular(f"Set MTU {mtu} on {intf_name}")

    ip_addr = intf_data.get("ip_address") or intf_data.get("ip_address_virtual")
    if ip_addr:
        is_anycast = ip_addr in anycast_ips
        vrf_name = intf_data.get("vrf", "vrf-ceos-dc1-prod-underlay")
        vrf = vrfs.get(vrf_name, vrfs["vrf-ceos-dc1-prod-underlay"])
        tenant_name = "dc1-production-anycast" if is_anycast else "dc1-production-underlay"
        tenant = get_or_create_tenant(tenant_name, tenant_name.lower().replace(" ", "-"))
        description = f"{'VLAN' if intf_type == 'vlan_interfaces' else intf_name} IP for {device.name}"

        print_regular(f"Processing IP {ip_addr} for {intf_name}, is_anycast: {is_anycast}")

        existing_ip = nb.ipam.ip_addresses.get(interface_id=interface.id, address=ip_addr)
        if existing_ip:
            needs_update = False
            if existing_ip.role != ("anycast" if is_anycast else None):
                needs_update = True
            if existing_ip.description != description:
                needs_update = True
            if existing_ip.status != "active":
                needs_update = True
            if existing_ip.tenant != tenant.id:
                needs_update = True
            if existing_ip.vrf != vrf.id:
                needs_update = True

            if needs_update:
                existing_ip.role = "anycast" if is_anycast else None
                existing_ip.description = description
                existing_ip.status = "active"
                existing_ip.tenant = tenant.id
                existing_ip.vrf = vrf.id
                existing_ip.save()
                print_regular(f"Updated existing {'Anycast ' if is_anycast else ''}IP {ip_addr} on {intf_name} with tenant {tenant.name} and VRF {vrf.name}")
            else:
                print_regular(f"{'Anycast ' if is_anycast else ''}IP {ip_addr} already correctly assigned to {intf_name}")
            return

        existing_ips = list(nb.ipam.ip_addresses.filter(address=ip_addr))

        if is_anycast or len(existing_ips) > 0:
            for ip in existing_ips:
                if (ip.tenant and ip.tenant.id == tenant.id and
                    ip.vrf and ip.vrf.id == vrf.id and
                    ip.description == description and
                    ip.status == "active"):
                    if ip.role != "anycast":
                        ip.role = "anycast"
                        ip.save()
                        print_regular(f"Updated existing IP {ip_addr} to Anycast role for {intf_name}")
                    if not ip.assigned_object or ip.assigned_object_id != interface.id:
                        ip.assigned_object_type = "dcim.interface"
                        ip.assigned_object_id = interface.id
                        ip.save()
                        print_regular(f"Assigned existing Anycast IP {ip_addr} to {intf_name} on {device.name} with tenant {tenant.name} and VRF {vrf.name} (IP ID: {ip.id})")
                        return
            try:
                new_ip = nb.ipam.ip_addresses.create(
                    address=ip_addr,
                    status="active",
                    assigned_object_type="dcim.interface",
                    assigned_object_id=interface.id,
                    description=description,
                    role="anycast",
                    tenant=tenant.id,
                    vrf=vrf.id
                )
                print_regular(f"Created new Anycast IP {ip_addr} for {intf_name} on {device.name} with tenant {tenant.name} and VRF {vrf.name} (IP ID: {new_ip.id})")
            except pynetbox.core.query.RequestError as e:
                print_error(f"Failed to create Anycast IP {ip_addr} for {intf_name}: {e}")
                existing_ip = nb.ipam.ip_addresses.get(address=ip_addr, assigned_object_id=interface.id)
                if existing_ip:
                    print_regular(f"Anycast IP {ip_addr} already exists and is assigned to {intf_name} (IP ID: {existing_ip.id})")
                else:
                    print_warning(f"Could not verify Anycast IP {ip_addr} assignment for {intf_name}")
            return

        for ip in existing_ips:
            if (ip.tenant and ip.tenant.id == tenant.id and
                ip.role is None and
                ip.description == description and
                ip.status == "active" and
                ip.vrf and ip.vrf.id == vrf.id):
                if not ip.assigned_object:
                    ip.assigned_object_type = "dcim.interface"
                    ip.assigned_object_id = interface.id
                    ip.save()
                    print_regular(f"Reused existing IP {ip_addr} for {intf_name} on {device.name} with tenant {tenant.name} and VRF {vrf.name} (IP ID: {ip.id})")
                    return
                elif ip.assigned_object_id == interface.id:
                    print_regular(f"IP {ip_addr} already correctly assigned to {intf_name}")
                    return
                else:
                    print_warning(f"IP {ip_addr} assigned to another interface, skipping for {intf_name}")
                    return

        try:
            new_ip = nb.ipam.ip_addresses.create(
                address=ip_addr,
                status="active",
                assigned_object_type="dcim.interface",
                assigned_object_id=interface.id,
                description=description,
                tenant=tenant.id,
                vrf=vrf.id
            )
            print_regular(f"Created new IP {ip_addr} for {intf_name} on {device.name} with tenant {tenant.name} and VRF {vrf.name} (IP ID: {new_ip.id})")
        except pynetbox.core.query.RequestError as e:
            print_error(f"Failed to create IP {ip_addr} for {intf_name}: {e}")

def update_management_interface(device, mgmt_intf_data, anycast_ips, vrfs):
    """Update or create the management interface and its IP, ensuring proper VRF and Anycast handling."""
    intf_name = mgmt_intf_data["name"]
    interface = nb.dcim.interfaces.get(device_id=device.id, name=intf_name)
    if not interface:
        print_regular(f"Creating new Management interface {intf_name} for {device.name}")
        interface = nb.dcim.interfaces.create(
            device=device.id,
            name=intf_name,
            type="1000base-t",
            description=mgmt_intf_data.get("description", ""),
            enabled=not mgmt_intf_data.get("shutdown", False)
        )
        time.sleep(1)
    else:
        interface.description = mgmt_intf_data.get("description", interface.description)
        interface.enabled = not mgmt_intf_data.get("shutdown", False)
        interface.save()

    mtu = mgmt_intf_data.get("mtu", DEFAULT_MTU)
    if interface.mtu != mtu:
        interface.mtu = mtu
        interface.save()
        print_regular(f"Set MTU {mtu} on {intf_name}")

    new_ip_addr = mgmt_intf_data.get("ip_address")
    if new_ip_addr:
        is_anycast = new_ip_addr in anycast_ips
        vrf_name = mgmt_intf_data.get("vrf", "vrf-ceos-dc1-prod-underlay")
        vrf = vrfs.get(vrf_name, vrfs["vrf-ceos-dc1-prod-underlay"])
        tenant_name = "dc1-production-anycast" if is_anycast else "dc1-production-underlay"
        tenant = get_or_create_tenant(tenant_name, tenant_name.lower().replace(" ", "-"))
        description = f"{intf_name} IP for {device.name}"

        print_regular(f"Processing IP {new_ip_addr} for {intf_name}, is_anycast: {is_anycast}")

        existing_ip = nb.ipam.ip_addresses.get(interface_id=interface.id, address=new_ip_addr)
        if existing_ip:
            needs_update = False
            if existing_ip.role != ("anycast" if is_anycast else None):
                needs_update = True
            if existing_ip.description != description:
                needs_update = True
            if existing_ip.status != "active":
                needs_update = True
            if existing_ip.tenant != tenant.id:
                needs_update = True
            if existing_ip.vrf != vrf.id:
                needs_update = True

            if needs_update:
                existing_ip.role = "anycast" if is_anycast else None
                existing_ip.description = description
                existing_ip.status = "active"
                existing_ip.tenant = tenant.id
                existing_ip.vrf = vrf.id
                existing_ip.save()
                print_regular(f"Updated existing {'Anycast ' if is_anycast else ''}IP {new_ip_addr} on {intf_name} with tenant {tenant.name} and VRF {vrf.name}")
            else:
                print_regular(f"{'Anycast ' if is_anycast else ''}IP {new_ip_addr} already correctly assigned to {intf_name}")
            return existing_ip

        if is_anycast or len(list(nb.ipam.ip_addresses.filter(address=new_ip_addr))) > 0:
            existing_ips = list(nb.ipam.ip_addresses.filter(address=new_ip_addr))
            for ip in existing_ips:
                if (ip.tenant and ip.tenant.id == tenant.id and
                    ip.vrf and ip.vrf.id == vrf.id and
                    ip.description == description and
                    ip.status == "active"):
                    if ip.role != "anycast":
                        ip.role = "anycast"
                        ip.save()
                        print_regular(f"Updated existing IP {new_ip_addr} to Anycast role for {intf_name}")
                    if not ip.assigned_object or ip.assigned_object_id != interface.id:
                        ip.assigned_object_type = "dcim.interface"
                        ip.assigned_object_id = interface.id
                        ip.save()
                        print_regular(f"Assigned existing Anycast IP {new_ip_addr} to {intf_name} on {device.name} with tenant {tenant.name} and VRF {vrf.name} (IP ID: {ip.id})")
                        return
            try:
                new_ip = nb.ipam.ip_addresses.create(
                    address=new_ip_addr,
                    status="active",
                    assigned_object_type="dcim.interface",
                    assigned_object_id=interface.id,
                    description=description,
                    role="anycast",
                    tenant=tenant.id,
                    vrf=vrf.id
                )
                print_regular(f"Created new Anycast IP {new_ip_addr} for {intf_name} on {device.name} with tenant {tenant.name} and VRF {vrf.name} (IP ID: {new_ip.id})")
                return new_ip
            except pynetbox.core.query.RequestError as e:
                print_error(f"Failed to create Anycast IP {new_ip_addr} for {intf_name}: {e}")
                existing_ip = nb.ipam.ip_addresses.get(address=new_ip_addr, assigned_object_id=interface.id)
                if existing_ip:
                    print_regular(f"Anycast IP {new_ip_addr} already exists and is assigned to {intf_name} (IP ID: {existing_ip.id})")
                    return existing_ip
                else:
                    print_warning(f"Could not verify Anycast IP {new_ip_addr} assignment for {intf_name}")
                    return None

        existing_ips = list(nb.ipam.ip_addresses.filter(address=new_ip_addr))
        for ip in existing_ips:
            if (ip.tenant and ip.tenant.id == tenant.id and
                ip.role is None and
                ip.description == description and
                ip.status == "active" and
                ip.vrf and ip.vrf.id == vrf.id):
                if not ip.assigned_object:
                    ip.assigned_object_type = "dcim.interface"
                    ip.assigned_object_id = interface.id
                    ip.save()
                    print_regular(f"Reused existing IP {new_ip_addr} for {intf_name} on {device.name} with tenant {tenant.name} and VRF {vrf.name} (IP ID: {ip.id})")
                    return ip
                elif ip.assigned_object_id == interface.id:
                    print_regular(f"IP {new_ip_addr} already correctly assigned to {intf_name}")
                    return ip
                else:
                    print_warning(f"IP {new_ip_addr} assigned to another interface, skipping for {intf_name}")
                    return ip

        try:
            new_ip = nb.ipam.ip_addresses.create(
                address=new_ip_addr,
                status="active",
                assigned_object_type="dcim.interface",
                assigned_object_id=interface.id,
                description=description,
                tenant=tenant.id,
                vrf=vrf.id
            )
            print_regular(f"Created new IP {new_ip_addr} for {intf_name} on {device.name} with tenant {tenant.name} and VRF {vrf.name} (IP ID: {new_ip.id})")
            return new_ip
        except pynetbox.core.query.RequestError as e:
            print_error(f"Failed to create IP {new_ip_addr} for {intf_name}: {e}")
            return None

    return None

def verify_anycast_assignments(device, anycast_ips, vrfs):
    """Verify and fix Anycast IP assignments for all interfaces on the device."""
    yaml_file = os.path.join(CONFIG_DIR, f"{device.name}.yml")
    if not os.path.exists(yaml_file):
        yaml_file = os.path.join(CONFIG_DIR, f"{device.name}.yaml")
    if not os.path.exists(yaml_file):
        print_error(f"No configuration file found for {device.name} in {CONFIG_DIR}")
        return

    with open(yaml_file, "r") as f:
        config = yaml.safe_load(f)
        for intf_type, intfs in [
            ("management_interfaces", config.get("management_interfaces", [])),
            ("ethernet_interfaces", config.get("ethernet_interfaces", [])),
            ("vlan_interfaces", config.get("vlan_interfaces", [])),
            ("loopback_interfaces", config.get("loopback_interfaces", [])),
            ("port_channel_interfaces", config.get("port_channel_interfaces", []))
        ]:
            for intf_data in intfs:
                intf = nb.dcim.interfaces.get(device_id=device.id, name=intf_data["name"])
                if not intf:
                    continue
                ip_addr = intf_data.get("ip_address") or intf_data.get("ip_address_virtual")
                if ip_addr and (ip_addr in anycast_ips or len(list(nb.ipam.ip_addresses.filter(address=ip_addr))) > 0):
                    vrf_name = intf_data.get("vrf", "vrf-ceos-dc1-prod-underlay")
                    vrf = vrfs.get(vrf_name, vrfs["vrf-ceos-dc1-prod-underlay"])
                    tenant = get_or_create_tenant("dc1-production-anycast", "dc1-production-anycast")
                    description = f"{'VLAN' if intf_type == 'vlan_interfaces' else intf.name} IP for {device.name}"
                    existing_ip = nb.ipam.ip_addresses.get(interface_id=intf.id, address=ip_addr)

                    if existing_ip:
                        if (existing_ip.role == "anycast" and
                            existing_ip.description == description and
                            existing_ip.tenant.id == tenant.id and
                            existing_ip.vrf.id == vrf.id and
                            existing_ip.status == "active"):
                            print_regular(f"Anycast IP {ip_addr} already correctly assigned to {intf.name}")
                        else:
                            existing_ip.role = "anycast"
                            existing_ip.description = description
                            existing_ip.tenant = tenant.id
                            existing_ip.vrf = vrf.id
                            existing_ip.status = "active"
                            existing_ip.save()
                            print_regular(f"Updated Anycast IP {ip_addr} assignment for {intf.name}")
                    else:
                        try:
                            new_ip = nb.ipam.ip_addresses.create(
                                address=ip_addr,
                                status="active",
                                assigned_object_type="dcim.interface",
                                assigned_object_id=intf.id,
                                description=description,
                                role="anycast",
                                tenant=tenant.id,
                                vrf=vrf.id
                            )
                            print_regular(f"Created new Anycast IP {ip_addr} for {intf.name} on {device.name} with tenant {tenant.name} and VRF {vrf.name} (IP ID: {new_ip.id})")
                        except pynetbox.core.query.RequestError as e:
                            print_error(f"Failed to create Anycast IP {ip_addr} for {intf.name} in verify: {e}")
                            existing_ip = nb.ipam.ip_addresses.get(address=ip_addr, assigned_object_id=intf.id)
                            if existing_ip:
                                print_regular(f"Anycast IP {ip_addr} already exists and is assigned to {intf.name} (IP ID: {existing_ip.id})")

def import_device_from_yaml(yaml_file):
    with open(yaml_file, "r") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print_error(f"Error parsing YAML file {yaml_file}: {e}")
            return

    hostname = config.get("hostname")
    if not hostname:
        print_warning(f"No hostname found in {yaml_file}. Skipping.")
        return

    device = nb.dcim.devices.get(name=hostname)
    if not device:
        print_error(f"Device {hostname} not found in NetBox. Please create it with basic info first.")
        return
    else:
        print_regular(f"Found existing device {hostname} (ID: {device.id})")

    anycast_ips, prefixes = collect_ip_usage_and_prefixes(hostname)

    vrfs = {
        "MGMT": get_or_create_vrf("MGMT", "dc1-production-mgmt", "dc1-production-mgmt"),
        "VRF10": get_or_create_vrf("VRF10", "dc1-production-vrf10", "dc1-production-vrf10"),
        "VRF11": get_or_create_vrf("VRF11", "dc1-production-vrf11", "dc1-production-vrf11"),
        "vrf-ceos-dc1-prod-underlay": get_or_create_vrf("vrf-ceos-dc1-prod-underlay", "dc1-production-underlay", "dc1-production-underlay")
    }

    create_prefixes(prefixes, vrfs)

    device.serial = config.get("serial_number", device.serial)
    device.platform = nb.dcim.platforms.get(slug="eos") or nb.dcim.platforms.create(name="EOS", slug="eos")
    device.status = "active"

    new_ip = None
    mgmt_interfaces = config.get("management_interfaces", [])
    if mgmt_interfaces:
        mgmt_intf = mgmt_interfaces[0]
        new_ip = update_management_interface(device, mgmt_intf, anycast_ips, vrfs)
    else:
        if device.primary_ip4:
            device.primary_ip4 = None
        if device.oob_ip:
            device.oob_ip = None

    for intf_type, intfs in [
        ("ethernet_interfaces", config.get("ethernet_interfaces", [])),
        ("vlan_interfaces", config.get("vlan_interfaces", [])),
        ("loopback_interfaces", config.get("loopback_interfaces", [])),
        ("port_channel_interfaces", config.get("port_channel_interfaces", []))
    ]:
        for intf_data in intfs:
            update_interface(device, intf_data, intf_type.split("_")[0], anycast_ips, vrfs)

    device.config_context = config
    try:
        device.save()
        print_regular(f"Step 1: Saved {hostname} with interfaces and config_context")
    except pynetbox.core.query.RequestError as e:
        print_error(f"Step 1 failed for {hostname}: {e}")
        return

    verify_anycast_assignments(device, anycast_ips, vrfs)

    if new_ip:
        device = nb.dcim.devices.get(id=device.id)  # Refresh device object
        ip_changed = False

        ip = nb.ipam.ip_addresses.get(id=new_ip.id) if new_ip else None
        interface = nb.dcim.interfaces.get(device_id=device.id, name="Management0")

        if interface and ip and ip.assigned_object and ip.assigned_object.id == interface.id:
            if device.primary_ip4 != new_ip.id:
                device.primary_ip4 = new_ip.id
                ip_changed = True
                print_regular(f"Set primary_ip4 to {new_ip.address} (IP ID: {new_ip.id})")

            if device.oob_ip != new_ip.id:
                device.oob_ip = new_ip.id
                ip_changed = True
                print_regular(f"Set oob_ip to {new_ip.address} (IP ID: {new_ip.id})")
        else:
            if interface and ip:
                if not ip.assigned_object or ip.assigned_object.id != interface.id:
                    ip.assigned_object_type = "dcim.interface"
                    ip.assigned_object_id = interface.id
                    ip.save()
                    print_regular(f"Reassigned management IP {new_ip.address} to interface {interface.name}")

                if device.primary_ip4 != new_ip.id:
                    device.primary_ip4 = new_ip.id
                    ip_changed = True
                    print_regular(f"Set primary_ip4 to {new_ip.address} (IP ID: {new_ip.id})")

                if device.oob_ip != new_ip.id:
                    device.oob_ip = new_ip.id
                    ip_changed = True
                    print_regular(f"Set oob_ip to {new_ip.address} (IP ID: {new_ip.id})")

        if ip_changed:
            try:
                device.save()
                print_regular(f"Step 2: Updated IP fields for {hostname}")
            except pynetbox.core.query.RequestError as e:
                print_error(f"Step 2 failed for {hostname}: {e}")
                return

    print_regular(f"Successfully updated {hostname}")

def main():
    if not os.path.exists(CONFIG_DIR):
        print_warning(f"Config directory {CONFIG_DIR} not found.")
        return

    device_name = input("Enter the device name to update in NetBox: ").strip()
    yaml_file = os.path.join(CONFIG_DIR, f"{device_name}.yml")
    if not os.path.exists(yaml_file):
        yaml_file = os.path.join(CONFIG_DIR, f"{device_name}.yaml")
    if not os.path.exists(yaml_file):
        print_error(f"No configuration file found for {device_name} in {CONFIG_DIR}")
        return

    print_regular(f"Processing {yaml_file}")
    import_device_from_yaml(yaml_file)

if __name__ == "__main__":
    main()
