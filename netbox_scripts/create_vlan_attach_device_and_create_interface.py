from extras.scripts import Script, IntegerVar, StringVar, ObjectVar, ChoiceVar
from ipam.models import VLAN, Prefix, IPAddress, VRF, Role as IPRole
from ipam.choices import IPAddressRoleChoices
from dcim.models import Site, Device, DeviceRole, Interface
from dcim.choices import InterfaceTypeChoices
from tenancy.models import Tenant, TenantGroup
from extras.models import Tag
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CreateVlanAndAttachDevicesInterfaces(Script):
    name = "Create VLAN Attach Tags Create Interfaces on Devices"
    description = "Creates a VLAN, prefix, anycast IPs with tags, and interfaces on l3leaf devices; Gitea Actions will sync changes."

    vlan_id = IntegerVar(description="VLAN ID (1-4094)", min_value=1, max_value=4094)
    vlan_name = StringVar(description="VLAN Name")
    vlan_role = ObjectVar(description="VLAN Role", model=IPRole, required=True)
    vlan_site = ObjectVar(description="Site", model=Site, required=True)
    vlan_tenant_group = ObjectVar(description="Tenant Group (for reference)", model=TenantGroup, required=False)
    vlan_tenant = ObjectVar(description="Tenant", model=Tenant, required=False)

    prefix = StringVar(description="Prefix (e.g., 10.0.1.0/24)", required=False)
    prefix_vrf = ObjectVar(description="VRF", model=VRF, required=False)
    prefix_vlan_id = IntegerVar(description="VLAN ID for Prefix Assignment (1-4094)", min_value=1, max_value=4094, required=False)
    prefix_tenant = ObjectVar(description="Tenant", model=Tenant, required=False)

    ip_address = StringVar(description="IP Address (e.g., 10.0.1.1/24, must be in prefix)", required=False)
    ip_role = ChoiceVar(
        description="Role",
        choices=[
            ("secondary", "Secondary"),
            ("anycast", "Anycast"),
            ("vip", "VIP"),
            ("vrrp", "VRRP"),
            ("hsrp", "HSRP"),
            ("glbp", "GLBP"),
            ("carp", "CARP"),
            ("loopback", "Loopback"),
        ],
        required=False
    )

    def get_applicable_tags(self, vlan):
        """Get tags that match device names in site dc1 with l2leaf or l3leaf roles"""
        try:
            dc1_site = Site.objects.get(slug='dc1')
            self.log_info(f"Found site: {dc1_site.name}")

            l2leaf_role = DeviceRole.objects.filter(slug='l2leaf').first()
            l3leaf_role = DeviceRole.objects.filter(slug='l3leaf').first()
            roles = [role for role in [l2leaf_role, l3leaf_role] if role]
            self.log_info(f"Found roles: {[role.name for role in roles]}")

            devices = Device.objects.filter(
                site=dc1_site,
                role__in=roles
            )
            device_names = set(device.name for device in devices)
            self.log_info(f"Found devices: {list(device_names)}")

            all_tags = Tag.objects.all()
            self.log_info(f"All available tags: {[tag.name for tag in all_tags]}")

            vlan_content_type = ContentType.objects.get(app_label='ipam', model='vlan')

            applicable_tags = [
                tag for tag in all_tags
                if tag.name in device_names
                and vlan_content_type in tag.object_types.all()
            ]

            self.log_info(f"Applicable tags: {[tag.name for tag in applicable_tags]}")
            return applicable_tags

        except Site.DoesNotExist:
            self.log_warning("Site 'dc1' not found")
            return []
        except Exception as e:
            logger.error(f"Error getting applicable tags: {str(e)}")
            return []

    def create_anycast_interfaces(self, vlan, ip_address_str, vrf, ip_role, tenant, commit):
        """Create interfaces on l3leaf devices with individual anycast IPs"""
        try:
            dc1_site = Site.objects.get(slug='dc1')
            l3leaf_role = DeviceRole.objects.filter(slug='l3leaf').first()
            if not l3leaf_role:
                self.log_warning("No 'l3leaf' role found")
                return

            l3leaf_devices = Device.objects.filter(
                site=dc1_site,
                role=l3leaf_role
            )
            self.log_info(f"Found l3leaf devices: {[device.name for device in l3leaf_devices]}")

            if not l3leaf_devices:
                self.log_warning("No devices with role 'l3leaf' found in site 'dc1'")
                return

            interface_name = f"Vlan{vlan.vid}"  # e.g., Vlan49
            description = vlan.name  # VLAN name as description
            interface_content_type = ContentType.objects.get(app_label='dcim', model='interface')

            for device in l3leaf_devices:
                self.log_info(f"Processing device: {device.name}")

                # Check if interface already exists
                interface = Interface.objects.filter(device=device, name=interface_name).first()
                if interface:
                    self.log_info(f"Interface {interface_name} already exists on {device.name}, checking IP assignment")
                    # Check if an IP with the same address is already assigned
                    existing_ip = interface.ip_addresses.filter(address=ip_address_str).first()
                    if existing_ip:
                        self.log_info(f"IP {ip_address_str} already assigned to {interface_name} on {device.name}, skipping")
                        continue
                    # Create a new IP address for this interface
                    ip = IPAddress(
                        address=ip_address_str,
                        vrf=vrf,
                        role=ip_role,
                        tenant=tenant,
                        assigned_object_type=interface_content_type,
                        assigned_object_id=interface.id,
                        description=f"VLAN IP for {device.name}"
                    )
                    if commit:
                        ip.save()
                        self.log_success(f"Created new IP address {ip.address} and assigned to existing interface {interface_name} on {device.name}")
                        # Verify assignment
                        interface.refresh_from_db()
                        if ip in interface.ip_addresses.all():
                            self.log_info(f"Verified: IP {ip.address} is assigned to {interface_name} on {device.name}")
                        else:
                            self.log_warning(f"IP {ip.address} assignment to {interface_name} on {device.name} failed verification")
                    else:
                        self.log_info(f"Dry-run: Would have created new IP {ip_address_str} and assigned to existing interface {interface_name} on {device.name}")
                    continue

                # Create new interface
                interface = Interface(
                    device=device,
                    name=interface_name,
                    type=InterfaceTypeChoices.TYPE_OTHER,
                    description=description,
                    vrf=vrf
                )
                # Create a new IP address for this interface
                ip = IPAddress(
                    address=ip_address_str,
                    vrf=vrf,
                    role=ip_role,
                    tenant=tenant,
                    description=f"VLAN IP for {device.name}"
                )
                if commit:
                    try:
                        interface.save()
                        self.log_info(f"Created interface {interface_name} on {device.name}")
                        # Assign the interface to the IP address
                        ip.assigned_object_type = interface_content_type
                        ip.assigned_object_id = interface.id
                        ip.save()
                        self.log_success(f"Created new IP address {ip.address} and assigned to interface {interface_name} on {device.name}")
                        # Verify assignment
                        interface.refresh_from_db()
                        if ip in interface.ip_addresses.all():
                            self.log_info(f"Verified: IP {ip.address} is assigned to {interface_name} on {device.name}")
                        else:
                            self.log_warning(f"IP {ip.address} assignment to {interface_name} on {device.name} failed verification")
                    except Exception as e:
                        self.log_failure(f"Failed to create interface {interface_name} or IP on {device.name}: {str(e)}")
                        continue
                else:
                    self.log_info(f"Dry-run: Would have created interface {interface_name} on {device.name} with new IP {ip_address_str}")

        except Site.DoesNotExist:
            self.log_warning("Site 'dc1' not found for interface creation")
        except Exception as e:
            logger.error(f"Error creating interfaces: {str(e)}")

    def run(self, data, commit):
        self.log_info(f"Running script with commit={commit}")

        vlan_id = data["vlan_id"]
        vlan_name = data["vlan_name"]
        vlan_role = data["vlan_role"]
        vlan_site = data["vlan_site"]
        vlan_tenant_group = data["vlan_tenant_group"]
        vlan_tenant = data["vlan_tenant"]

        if vlan_tenant_group and not vlan_tenant:
            try:
                vlan_tenant = Tenant.objects.filter(group=vlan_tenant_group).first()
                if vlan_tenant:
                    self.log_info(f"Auto-selected Tenant: {vlan_tenant} based on Tenant Group {vlan_tenant_group}")
            except Exception as e:
                logger.error(f"Error filtering tenant by group: {e}")
                vlan_tenant = None

        prefix_str = data["prefix"] if data["prefix"] else ""
        prefix_vrf = data["prefix_vrf"]
        prefix_vlan_id = data["prefix_vlan_id"]
        prefix_tenant = data["prefix_tenant"]

        ip_address_str = data["ip_address"] if data["ip_address"] else ""
        ip_role_name = data["ip_role"]

        with transaction.atomic():
            vlan = VLAN(
                vid=vlan_id,
                name=vlan_name,
                role=vlan_role,
                site=vlan_site,
                tenant=vlan_tenant,
            )

            if commit:
                vlan.save()
                self.log_success(f"Created VLAN: {vlan}")

                tags = self.get_applicable_tags(vlan)
                if tags:
                    vlan.tags.set(tags)
                    self.log_info(f"Applied tags to VLAN: {[tag.name for tag in tags]}")
                else:
                    self.log_info("No matching tags found for VLAN")
            else:
                self.log_info(f"Dry-run: Would have created VLAN: {vlan}")
                tags = self.get_applicable_tags(vlan)
                if tags:
                    self.log_info(f"Dry-run: Would have applied tags to VLAN: {[tag.name for tag in tags]}")
                else:
                    self.log_info("No matching tags found for VLAN")

            if prefix_str and prefix_vrf:
                prefix_vlan = vlan
                prefix = Prefix(
                    prefix=prefix_str,
                    vrf=prefix_vrf,
                    vlan=prefix_vlan,
                    tenant=prefix_tenant,
                )
                if commit:
                    prefix.save()
                    self.log_success(f"Created Prefix: {prefix} in VRF: {prefix_vrf}")
                else:
                    self.log_info(f"Dry-run: Would have created Prefix: {prefix}")
            else:
                self.log_info("No prefix provided, skipping prefix creation")

            if ip_address_str and prefix_vrf:
                ip_role = None
                if ip_role_name:
                    ip_role_mapping = {
                        "secondary": IPAddressRoleChoices.ROLE_SECONDARY,
                        "anycast": IPAddressRoleChoices.ROLE_ANYCAST,
                        "vip": IPAddressRoleChoices.ROLE_VIP,
                        "vrrp": IPAddressRoleChoices.ROLE_VRRP,
                        "hsrp": IPAddressRoleChoices.ROLE_HSRP,
                        "glbp": IPAddressRoleChoices.ROLE_GLBP,
                        "carp": IPAddressRoleChoices.ROLE_CARP,
                        "loopback": IPAddressRoleChoices.ROLE_LOOPBACK,
                    }
                    ip_role = ip_role_mapping.get(ip_role_name.lower())

                # For non-anycast IPs, create a single IP address
                if ip_role != IPAddressRoleChoices.ROLE_ANYCAST:
                    interface_content_type = ContentType.objects.get(app_label='dcim', model='interface')
                    ip = IPAddress(
                        address=ip_address_str,
                        vrf=prefix_vrf,
                        role=ip_role,
                        tenant=prefix_tenant,
                    )
                    if commit:
                        ip.save()
                        self.log_success(f"Created IP Address: {ip} with role {ip_role_name if ip_role_name else 'None'}")
                    else:
                        self.log_info(f"Dry-run: Would have created IP Address: {ip}")
                else:
                    # For anycast IPs, interfaces will be created with individual IPs
                    if commit:
                        self.log_info(f"Creating anycast IPs for l3leaf devices with address {ip_address_str}")
                        self.create_anycast_interfaces(vlan, ip_address_str, prefix_vrf, ip_role, prefix_tenant, commit)
                    else:
                        self.log_info(f"Dry-run: Would have created anycast IPs for l3leaf devices with address {ip_address_str}")
                        self.create_anycast_interfaces(vlan, ip_address_str, prefix_vrf, ip_role, prefix_tenant, commit)
            else:
                self.log_info("No IP address provided, skipping IP creation")

        self.log_info("All operations completed successfully!")
