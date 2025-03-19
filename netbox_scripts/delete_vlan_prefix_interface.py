from extras.scripts import Script, IntegerVar, ObjectVar
from ipam.models import VLAN, Prefix, IPAddress, VRF
from ipam.choices import IPAddressRoleChoices
from dcim.models import Site, Device, DeviceRole, Interface
from tenancy.models import Tenant, TenantGroup
from django.db import transaction
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeleteVlanAndAssociatedObjects(Script):
    name = "Delete VLAN and Associated Objects"
    description = "Deletes a VLAN, its prefix, anycast IPs, and interfaces on l3leaf devices."

    vlan_id = IntegerVar(description="VLAN ID to delete (1-4094)", min_value=1, max_value=4094)
    vlan_site = ObjectVar(description="Site of the VLAN", model=Site, required=True)
    vlan_tenant_group = ObjectVar(description="Tenant Group (for reference)", model=TenantGroup, required=False)
    vlan_tenant = ObjectVar(description="Tenant", model=Tenant, required=False)
    prefix_vrf = ObjectVar(description="VRF of the Prefix", model=VRF, required=False)

    def run(self, data, commit):
        self.log_info(f"Running script with commit={commit}")

        vlan_id = data["vlan_id"]
        vlan_site = data["vlan_site"]
        vlan_tenant_group = data["vlan_tenant_group"]
        vlan_tenant = data["vlan_tenant"]
        prefix_vrf = data["prefix_vrf"]

        if vlan_tenant_group and not vlan_tenant:
            try:
                vlan_tenant = Tenant.objects.filter(group=vlan_tenant_group).first()
                if vlan_tenant:
                    self.log_info(f"Auto-selected Tenant: {vlan_tenant} based on Tenant Group {vlan_tenant_group}")
            except Exception as e:
                logger.error(f"Error filtering tenant by group: {e}")
                vlan_tenant = None

        with transaction.atomic():
            # Step 1: Find the VLAN
            try:
                vlan = VLAN.objects.get(
                    vid=vlan_id,
                    site=vlan_site,
                    tenant=vlan_tenant if vlan_tenant else None
                )
                self.log_info(f"Found VLAN: {vlan}")
            except VLAN.DoesNotExist:
                self.log_failure(f"VLAN with ID {vlan_id} in site {vlan_site} not found")
                return
            except Exception as e:
                self.log_failure(f"Error finding VLAN: {str(e)}")
                return

            # Step 2: Find and delete associated prefix
            if prefix_vrf:
                try:
                    prefix = Prefix.objects.filter(
                        vlan=vlan,
                        vrf=prefix_vrf
                    ).first()
                    if prefix:
                        if commit:
                            prefix.delete()
                            self.log_success(f"Deleted Prefix: {prefix}")
                        else:
                            self.log_info(f"Dry-run: Would have deleted Prefix: {prefix}")
                    else:
                        self.log_info(f"No prefix found for VLAN {vlan} in VRF {prefix_vrf}")
                except Exception as e:
                    self.log_failure(f"Error deleting prefix: {str(e)}")
                    return
            else:
                self.log_info("No VRF provided, skipping prefix deletion")

            # Step 3: Find "l3leaf" devices
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
            except Site.DoesNotExist:
                self.log_warning("Site 'dc1' not found")
                return
            except Exception as e:
                self.log_failure(f"Error finding l3leaf devices: {str(e)}")
                return

            # Step 4: Delete interfaces and associated anycast IPs
            interface_name = f"Vlan{vlan_id}"  # e.g., Vlan49
            for device in l3leaf_devices:
                self.log_info(f"Processing device: {device.name}")
                try:
                    interface = Interface.objects.filter(device=device, name=interface_name).first()
                    if not interface:
                        self.log_info(f"No interface {interface_name} found on {device.name}, skipping")
                        continue

                    # Find and delete anycast IPs assigned to this interface
                    anycast_ips = IPAddress.objects.filter(
                        assigned_object_type__model='interface',
                        assigned_object_id=interface.id,
                        role=IPAddressRoleChoices.ROLE_ANYCAST
                    )
                    for ip in anycast_ips:
                        if commit:
                            ip.delete()
                            self.log_success(f"Deleted IP Address: {ip} from interface {interface_name} on {device.name}")
                        else:
                            self.log_info(f"Dry-run: Would have deleted IP Address: {ip} from interface {interface_name} on {device.name}")

                    # Delete the interface
                    if commit:
                        interface.delete()
                        self.log_success(f"Deleted interface {interface_name} on {device.name}")
                    else:
                        self.log_info(f"Dry-run: Would have deleted interface {interface_name} on {device.name}")

                except Exception as e:
                    self.log_failure(f"Error deleting interface or IPs on {device.name}: {str(e)}")
                    continue

            # Step 5: Delete the VLAN
            if commit:
                vlan.delete()
                self.log_success(f"Deleted VLAN: {vlan}")
            else:
                self.log_info(f"Dry-run: Would have deleted VLAN: {vlan}")

        self.log_info("All operations completed successfully!")
