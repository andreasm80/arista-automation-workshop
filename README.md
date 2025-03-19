# Lab contents
The following folders in this repo:\
avd_playbooks: content to update AVD from Netbox\
gitea_workflows: content for gitea actions\
import-scripts: Import devices to populate Netbox with devices, interfaces, vlans, prefix\
netbox_scripts: Custom scripts in Netbox\
webhook-server: webhook server in python to receive webhooks

Several of these scripts will be used during the workshop. In addition to these scripts we need to create a python environment, install some pip modules rquired by some of the scripts but also AVD itself, which will be installed as part of AVD installation.

## Some housekeeping rules.
All students will be provided with a student number. eg 1-15. This number will be used twice.\
All the elements in AVD, hostname, FABRIC, DC1 etc will have to use the prefix st1-dc1-leaf1a, ST1-FABRIC, ST1-DC1 etc\
Every student will use the third octet in the management IP address according to their number from a pool of /24 subnets. 
192.168.1.0/24 equals Student 1, 192.168.2.0/24 equals Student 2.

## Connecting to the guis of Netbox and Gitea
ssh -L 3030:localhost:3000 nlab@94.26.25.40\
ssh -L 3030:localhost:3000 -L 8080:localhost:80 nlab@94.26.25.40

http://localhost:8080/\
http://localhost:3030/user/settings/actions/runners


## Gitea preps
Create new registration token\
For runner to reactivate - delete /data/.runner restart runner\
docker compose down\
docker compose up -d

## AVD installation
```bash
nlab@nlab-101:~$ mkdir ci_cd_1
nlab@nlab-101:~$ cd ci_cd_1/
nlab@nlab-101:~/ci_cd_1$ python -m venv ci_cd_env
nlab@nlab-101:~/ci_cd_1$
nlab@nlab-101:~/ci_cd_1$ source ci_cd_env/bin/activate
(ci_cd_env) nlab@nlab-101:~/ci_cd_1$
(ci_cd_env) nlab@nlab-101:~/ci_cd_1$ pip install "pyavd[ansible]"
(ci_cd_env) nlab@nlab-101:~/ci_cd_1$ ansible-galaxy collection install arista.avd
(ci_cd_env) nlab@nlab-101:~/ci_cd_1$ ansible-playbook arista.avd.install_examples
```
Now the folder should look something like this:
```bash
(ci_cd_env) nlab@nlab-101:~/ci_cd_1$ ll
total 40
drwxrwxr-x 10 nlab nlab 4096 Mar 11 07:29 ./
drwxr-x--- 10 nlab nlab 4096 Mar 11 07:24 ../
drwxrwxr-x  7 nlab nlab 4096 Mar 11 07:28 campus-fabric/
drwxrwxr-x  5 nlab nlab 4096 Mar 11 07:21 ci_cd_env/
drwxrwxr-x  2 nlab nlab 4096 Mar 11 07:29 common/
drwxrwxr-x  8 nlab nlab 4096 Mar 11 07:26 cv-pathfinder/
drwxrwxr-x  7 nlab nlab 4096 Mar 11 07:27 dual-dc-l3ls/
drwxrwxr-x  7 nlab nlab 4096 Mar 11 07:29 isis-ldp-ipvpn/
drwxrwxr-x  7 nlab nlab 4096 Mar 11 07:28 l2ls-fabric/
drwxrwxr-x  7 nlab nlab 4096 Mar 11 07:29 single-dc-l3ls/
```


## Containerlab preps
ALl students must use their own management subnet\
All students ceos instances must start with the prefix "st1-" eg: "st1-dc1-spine1"

The eos Docker image: cEOS64-lab-4.33.0F.tar is needed

```bash
cat cEOS64-lab-4.33.0F.tar | docker import - ceos:4.33.0F
```


Containerlab topology yaml:
```yaml
# topology documentation: http://containerlab.dev/lab-examples/srl-ceos/
name: ci_cd_dev-env

mgmt:
  network: dev-ztp-ceos-mgmt    # management network name
  mtu: 9500
#  bridge: br-ceos-mgmt
  ipv4-subnet: 10.10.10.0/24       # ipv4 range
topology:
  defaults:
#    suppress-startup-config: true
    env:
      TOGGLE_OVERRIDE: CEosLabWithTrap=true
#        - CEosLabWithTrapV2=true
  nodes:
    node-21:
      kind: arista_ceos
      image: ceos:4.33.0F
      startup-config: node1-startup-config.cfg
      mgmt-ipv4: 10.10.10.11
    node-22:
      kind: arista_ceos
      image: ceos:4.33.0F
      startup-config: node2-startup-config.cfg
      mgmt-ipv4: 10.10.10.12
    node-23:
      kind: arista_ceos
      image: ceos:4.33.0F
      startup-config: node3-startup-config.cfg
      mgmt-ipv4: 10.10.10.13
    node-24:
      kind: arista_ceos
      image: ceos:4.33.0F
      startup-config: node4-startup-config.cfg
      mgmt-ipv4: 10.10.10.14
    node-25:
      kind: arista_ceos
      image: ceos:4.33.0F
      startup-config: node5-startup-config.cfg
      mgmt-ipv4: 10.10.10.15
    node-26:
      kind: arista_ceos
      image: ceos:4.33.0F
      startup-config: node6-startup-config.cfg
      mgmt-ipv4: 10.10.10.16
    node-27:
      kind: arista_ceos
      image: ceos:4.33.0F
      startup-config: node7-startup-config.cfg
      mgmt-ipv4: 10.10.10.17
    node-28:
      kind: arista_ceos
      image: ceos:4.33.0F
      startup-config: node8-startup-config.cfg
      mgmt-ipv4: 10.10.10.18



  links:
# Spine to leafs
# Spine 1
    - endpoints: ["node-21:eth1", "node-23:eth1"]
      mtu: 9500
    - endpoints: ["node-21:eth2", "node-24:eth1"]
      mtu: 9500
    - endpoints: ["node-21:eth3", "node-25:eth1"]
      mtu: 9500
    - endpoints: ["node-21:eth4", "node-26:eth1"]
      mtu: 9500
# Spine 2
    - endpoints: ["node-22:eth1", "node-23:eth2"]
      mtu: 9500
    - endpoints: ["node-22:eth2", "node-24:eth2"]
      mtu: 9500
    - endpoints: ["node-22:eth3", "node-25:eth2"]
      mtu: 9500
    - endpoints: ["node-22:eth4", "node-26:eth2"]
      mtu: 9500
# Leaf Group 1
# Mlag
    - endpoints: ["node-23:eth3", "node-24:eth3"]
      mtu: 9500
    - endpoints: ["node-23:eth4", "node-24:eth4"]
      mtu: 9500
# Downlink to Leaf1c
    - endpoints: ["node-23:eth6", "node-27:eth1"]
      mtu: 9500
    - endpoints: ["node-24:eth6", "node-27:eth2"]
      mtu: 9500
# Leaf Group 2
# Mlag
    - endpoints: ["node-25:eth3", "node-26:eth3"]
      mtu: 9500
    - endpoints: ["node-25:eth4", "node-26:eth4"]
      mtu: 9500
# Downlink to Leaf2c
    - endpoints: ["node-25:eth6", "node-28:eth1"]
      mtu: 9500
    - endpoints: ["node-26:eth6", "node-28:eth2"]
      mtu: 9500
```

Create SAH512 password:\
```bash
(ci_cd_env) nlab@nlab-101:~/containerlab/dc1-l3ls$ sudo apt update && sudo apt install whois -y

(ci_cd_env) nlab@nlab-101:~/containerlab/dc1-l3ls$ mkpasswd -m sha-512 nlabpassword
$6$ha2bCNAO5ioINUQa$3o.TfZ/aFd6Dzcp/ercTW7uY/V/INLhP2uByuFpoV.7zHqjCrhqPmE28zznt4r7CeBu.hBOHialeechWfNIrA1
```

Add the Terminattr agent in the node-startup configs:

```bash
!
daemon TerminAttr
   exec /usr/bin/TerminAttr -cvaddr=94.26.25.51:9910 -cvauth=token,/tmp/token -cvvrf=MGMT -disableaaa -smashexcludes=ale,flexCounter,hardware,kni,pulse,strata -ingestexclude=/Sysdb/cell/1/agent,/Sysdb/cell/2/agent -taillogs
   no shutdown
!
hostname st1-dc1-spine1
```

Full example from spine1:
```bash
!
daemon TerminAttr
   exec /usr/bin/TerminAttr -cvaddr=94.26.25.51:9910 -cvauth=token,/tmp/token -cvvrf=MGMT -disableaaa -smashexcludes=ale,flexCounter,hardware,kni,pulse,strata -ingestexclude=/Sysdb/cell/1/agent,/Sysdb/cell/2/agent -taillogs
   no shutdown
!
hostname st1-dc1-spine1
!
! Configures username and password for the ansible user
username ansible privilege 15 role network-admin secret sha512 $6$ha2bCNAO5ioINUQa$3o.TfZ/aFd6Dzcp/ercTW7uY/V/INLhP2uByuFpoV.7zHqjCrhqPmE28zznt4r7CeBu.hBOHialeechWfNIrA1
!
! Defines the VRF for MGMT
vrf instance MGMT
!
! Defines the settings for the Management1 interface through which Ansible reaches the device
interface Management0
   description oob_management
   no shutdown
   vrf MGMT
   ! IP address - must be set uniquely per device
   ip address 10.10.10.11/24
!
! Static default route for VRF MGMT
ip route vrf MGMT 0.0.0.0/0 10.10.10.1
!
! Enables API access in VRF MGMT
management api http-commands
   protocol https
   no shutdown
   !
   vrf MGMT
      no shutdown
!
end
!
! Save configuration to flash
copy running-config startup-config
```


## Ansible and Netbox preps - some dependecies
Inside the same environment as above (ci_cd_env):
```bash
pip install requests pynetbox
ansible-galaxy collection install netbox.netbox
export NETBOX_URL="http://netbox.example.com"
export NETBOX_TOKEN="your-api-token"
```

## Create git repo for the AVD project folder
Add SSH key to Gitea:
```bash
(ci_cd_env) nlab@nlab-101:~/ci_cd_1$ ssh-keygen -t ed25519 -C "user@user.com"
Generating public/private ed25519 key pair.
Enter file in which to save the key (/home/nlab/.ssh/id_ed25519):
Enter passphrase (empty for no passphrase):
Enter same passphrase again:
Your identification has been saved in /home/nlab/.ssh/id_ed25519
Your public key has been saved in /home/nlab/.ssh/id_ed25519.pub
The key fingerprint is:
SHA256:vTqbfnvnrTkLTcZxzWdlWo49A2gVOmuB/KunapF8fRI user@user.com
The key's randomart image is:
+--[ED25519 256]--+
|            o+. +|
|        . .o. .Oo|
|         o.+  +oO|
|         ..E+. ++|
|      . S o+. +  |
|       + ..+.=   |
|        o ..+ .  |
|       ..oo...oo |
|      .o**+o o=+.|
+----[SHA256]-----+
(ci_cd_env) nlab@nlab-101:~/ci_cd_1$
```
Copy key to Gitea from here:
```bash
(ci_cd_env) nlab@nlab-101:~/ci_cd_1$ cat ~/.ssh/id_ed25519.pub
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHDIVB0srma74PXgxTLAwZOrhwtmEQRVkp61u83Zh0Vd user@user.com
```

```bash
git init
git checkout -b main
git add .
git commit -m "first commit"
git remote add origin git@localhost:admin/ci_cd_1.git
git push -u origin main
```
First time push accept fingerprint:
```bash
(ci_cd_env) nlab@nlab-101:~/ci_cd_1$ git push -u origin main
The authenticity of host 'localhost (127.0.0.1)' can't be established.
ED25519 key fingerprint is SHA256:Brzazyi79D8XpFzN7wX2dIoGpoVRDyDutZYAjNV5/Jk.
This key is not known by any other names.
Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
Warning: Permanently added 'localhost' (ED25519) to the list of known hosts.
Enumerating objects: 8387, done.
Counting objects: 100% (8387/8387), done.
Delta compression using up to 8 threads
Compressing objects: 100% (6886/6886), done.
Writing objects: 100% (8387/8387), 35.42 MiB | 15.27 MiB/s, done.
Total 8387 (delta 1381), reused 8387 (delta 1381), pack-reused 0
remote: Resolving deltas: 100% (1381/1381), done.
remote: . Processing 1 references
remote: Processed 1 references in total
To localhost:admin/ci_cd_1.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
(ci_cd_env) nlab@nlab-101:~/ci_cd_1$
```

## AVD inventory and group_vars
All users must use their ST1_ prefix as mentioned above, this also includes all the CONTAINER sections like FABRIC, DC1, DC1-SPINES, DC1_L3_LEAVES, DC1_L2_LEAVES  of inventory.yml. So FABRIC becomes ST1_FABRIC, ST1_DC1, ST1_DC1-SPINES etc. UNDERSCORE\
inventory.yml changes:
```yaml
---
all:
  children:
    CLOUDVISION:
      hosts:
        cvp:
          # Ansible variables used by the ansible_avd and ansible_cvp roles to push configuration to devices via CVP
          ansible_host: 94.26.25.51
          ansible_user: ansible
          ansible_password: nlabpassword
          ansible_connection: httpapi
          ansible_httpapi_use_ssl: true
          ansible_httpapi_validate_certs: false
          ansible_network_os: eos

    ST1_FABRIC:
      children:
        ST1_DC1:
          vars:
            mgmt_gateway: 10.10.10.1
          children:
            ST1_DC1_SPINES:
              hosts:
                st1-dc1-spine1:
                  ansible_host: 10.10.10.11
                st1-dc1-spine2:
                  ansible_host: 10.10.10.12
            ST1_DC1_L3_LEAVES:
              hosts:
                st1-dc1-leaf1a:
                  ansible_host: 10.10.10.13
                st1-dc1-leaf1b:
                  ansible_host: 10.10.10.14
                st1-dc1-leaf2a:
                  ansible_host: 10.10.10.15
                st1-dc1-leaf2b:
                  ansible_host: 10.10.10.16
            ST1_DC1_L2_LEAVES:
              hosts:
                st1-dc1-leaf1c:
                  ansible_host: 10.10.10.17
                st1-dc1-leaf2c:
                  ansible_host: 10.10.10.18

    NETWORK_SERVICES:
      children:
        ST1_DC1_L3_LEAVES:
        ST1_DC1_L2_LEAVES:
    CONNECTED_ENDPOINTS:
      children:
        ST1_DC1_L3_LEAVES:
        ST1_DC1_L2_LEAVES: 
```

This also means we need to rename the respective files under group_vars:
```bash
(ci_cd_env) nlab@nlab-101:~/ci_cd_1/single-dc-l3ls/group_vars$ ls
CONNECTED_ENDPOINTS.yml  ST1_DC1_L2_LEAVES.yml  ST1_DC1_L3_LEAVES.yml  ST1_DC1_SPINES.yml  ST1_DC1.yml  ST1_FABRIC.yml  NETWORK_SERVICES.yml
```

DC1.yml changes:
```yaml
---
mgmt_interface: Management0  # THIS
mgmt_interface_description: oob_management  # THIS
spine:
  defaults:
    platform: cEOS-lab  # THIS
    loopback_ipv4_pool: 10.255.0.0/27
    bgp_as: 65100
  nodes:
    - name: st1-dc1-spine1 # THIS
      id: 1
      mgmt_ip: 10.10.10.11/24 # THIS
    - name: st1-dc1-spine2 # THIS
      id: 2
      mgmt_ip: 10.10.10.12/24 # THIS
l3leaf:
  defaults:
    platform: vEOS-lab
    loopback_ipv4_pool: 10.255.0.0/27
    loopback_ipv4_offset: 2
    vtep_loopback_ipv4_pool: 10.255.1.0/27
    uplink_switches: ['st1-dc1-spine1', 'st1-dc1-spine2'] # THIS
    uplink_ipv4_pool: 10.255.255.0/26
    mlag_peer_ipv4_pool: 10.255.1.64/27
    mlag_peer_l3_ipv4_pool: 10.255.1.96/27
    virtual_router_mac_address: 00:1c:73:00:00:99
    spanning_tree_priority: 4096
    spanning_tree_mode: mstp
  node_groups:
    - group: ST1_DC1_L3_LEAF1 # THIS
      bgp_as: 65101
      nodes:
        - name: st1-dc1-leaf1a # THIS
          id: 1
          mgmt_ip: 10.10.10.13/24 # THIS
          uplink_switch_interfaces:
            - Ethernet1
            - Ethernet1
        - name: st1-dc1-leaf1b # THIS
          id: 2
          mgmt_ip: 10.10.10.14/24 # THIS
          uplink_switch_interfaces:
            - Ethernet2
            - Ethernet2
    - group: ST1_DC1_L3_LEAF2 # THIS
      bgp_as: 65102
      nodes:
        - name: st1-dc1-leaf2a # THIS
          id: 3
          mgmt_ip: 10.10.10.15/24 # THIS
          uplink_switch_interfaces:
            - Ethernet3
            - Ethernet3
        - name: st1-dc1-leaf2b # THIS
          id: 4
          mgmt_ip: 10.10.10.16/24 # THIS
          uplink_switch_interfaces:
            - Ethernet4
            - Ethernet4
l2leaf:
  defaults:
    platform: cEOS-lab # THIS
    spanning_tree_mode: mstp
  node_groups:
    - group: ST1_DC1_L2_LEAF1 # THIS
      uplink_switches: ['st1-dc1-leaf1a', 'st1-dc1-leaf1b'] # THIS
      nodes:
        - name: st1-dc1-leaf1c # THIS
          id: 1
          mgmt_ip: 10.10.10.17/24 # THIS
          uplink_switch_interfaces:
            - Ethernet6 # THIS
            - Ethernet6 # THIS
    - group: ST1_DC1_L2_LEAF2 # THIS
      uplink_switches: ['st1-dc1-leaf2a', 'st1-dc1-leaf2b'] # THIS
      nodes:
        - name: st1-dc1-leaf2c # THIS
          id: 2
          mgmt_ip: 10.10.10.18/24 # THIS
          uplink_switch_interfaces:
            - Ethernet6 # THIS
            - Ethernet6 # THIS
```

Also remember these parts when starting on the auto pipeline. They should be automatically updated when we start with the playbooks.
```yaml
        DC1:
          vars:
            mgmt_gateway: 172.18.100.2

      mgmt_ip: "{{ ansible_host }}/24"  
    - name: ceos-dc1-spine2
      id: 2
      mgmt_ip: "{{ ansible_host }}/24"
```

Then it is the FABRIC.yml file:

```yaml
---
ansible_connection: ansible.netcommon.httpapi
ansible_network_os: arista.eos.eos
ansible_user: ansible
ansible_password: nlabpassword # THIS
ansible_become: true
ansible_become_method: enable
ansible_httpapi_use_ssl: true # THIS?
ansible_httpapi_validate_certs: false
fabric_name: ST1_FABRIC # THIS
eos_designs_documentation:
  topology_csv: true
  p2p_links_csv: true
underlay_routing_protocol: ebgp
overlay_routing_protocol: ebgp
local_users:
  - name: ansible
    privilege: 15
    role: network-admin
    sha512_password: $6$ha2bCNAO5ioINUQa$3o.TfZ/aFd6Dzcp/ercTW7uY/V/INLhP2uByuFpoV.7zHqjCrhqPmE28zznt4r7CeBu.hBOHialeechWfNIrA1 # THIS
  - name: admin
    privilege: 15
    role: network-admin
    no_password: true
bgp_peer_groups:
  evpn_overlay_peers:
    password: Q4fqtbqcZ7oQuKfuWtNGRQ==
  ipv4_underlay_peers:
    password: 7x4B4rnJhZB438m9+BrBfQ==
  mlag_ipv4_underlay_peer:
    password: 4b21pAdCvWeAqpcKDFMdWw==
p2p_uplinks_mtu: 1500
default_interfaces:
  - types: [ spine ]
    platforms: [ default ]
    uplink_interfaces: [ Ethernet1-2 ]
    downlink_interfaces: [ Ethernet1-8 ]
  - types: [ l3leaf ]
    platforms: [ default ]
    uplink_interfaces: [ Ethernet1-2 ]
    mlag_interfaces: [ Ethernet3-4 ]
    downlink_interfaces: [ Ethernet8 ]
  - types: [ l2leaf ]
    platforms: [ default ]
    uplink_interfaces: [ Ethernet1-2 ]
cvp_instance_ips:
  - 94.26.25.51 # THIS
terminattr_smashexcludes: "ale,flexCounter,hardware,kni,pulse,strata"
terminattr_ingestexclude: "/Sysdb/cell/1/agent,/Sysdb/cell/2/agent"
terminattr_disable_aaa: true
name_servers:
  - 192.168.1.1
ntp_settings:
  server_vrf: use_mgmt_interface_vrf
  servers:
    - name: 0.pool.ntp.org

# These sections below
clock: 
  timezone: Europe/Oslo

sflow:
  sample: 16384
  polling_interval: 10
  destinations:
    - destination: 127.0.0.1
  source_interface: Loopback0
  run: true

lldp:
  run: true
```

Then it is the NETWORK_SERVICES.yml:

```yaml
---
tenants:
  # Definition of tenants. Additional level of abstraction to VRFs
  - name: TENANT1
    # Number used to generate the VNI of each VLAN by adding the VLAN number in this tenant.
    mac_vrf_vni_base: 10000
    vrfs:
      # VRF definitions inside the tenant.
      - name: VRF10
        # VRF VNI definition.
        vrf_vni: 10
        # Enable VTEP Network diagnostics
        # This will create a loopback with virtual source-nat enable to perform diagnostics from the switch.
        vtep_diagnostic:
          # Loopback interface number
          loopback: 10
          # Loopback ip range, a unique ip is derived from this ranged and assigned
          # to each l3 leaf based on it's unique id.
          loopback_ip_range: 10.255.10.0/27
        svis:
          # SVI definitions.
          - id: 11
            # SVI Description
            name: VRF10_VLAN11
            enabled: true
            # IP anycast gateway to be used in the SVI in every leaf.
            ip_address_virtual: 10.10.11.1/24
          - id: 12
            name: VRF10_VLAN12
            enabled: true
            ip_address_virtual: 10.10.12.1/24
      - name: VRF11
        vrf_vni: 11
        vtep_diagnostic:
          loopback: 11
          loopback_ip_range: 10.255.11.0/27
        svis:
          - id: 21
            name: VRF11_VLAN21
            enabled: true
            ip_address_virtual: 10.10.21.1/24
          - id: 22
            name: VRF11_VLAN22
            enabled: true
            ip_address_virtual: 10.10.22.1/24

    l2vlans:
      # These are pure L2 vlans. They do not have a SVI defined in the l3leafs and they will be bridged inside the VXLAN fabric
      - id: 3401
        name: L2_VLAN3401
      - id: 3402
        name: L2_VLAN3402
```

And finally the build.yml playbook itself:
```yaml
---
# build.yml

- name: Build Configurations and Documentation # (1)!
  hosts: ST1_FABRIC # THIS
  gather_facts: false
  tasks:

    - name: Generate AVD Structured Configurations and Fabric Documentation # (2)!
      ansible.builtin.import_role:
        name: arista.avd.eos_designs

    - name: Generate Device Configurations and Documentation # (3)!
      ansible.builtin.import_role:
        name: arista.avd.eos_cli_config_gen
```

And the deploy-cvp.yml playbook:
```yaml
---
- name: Deploy Configurations to Devices Using CloudVision Portal # (1)!
  hosts: CLOUDVISION
  gather_facts: false
  connection: local
  tasks:

    - name: Deploy Configurations to CloudVision # (2)!
      ansible.builtin.import_role:
        name: arista.avd.eos_config_deploy_cvp
      vars:
        cv_collection: v3 # (3)!
        fabric_name: ST1_FABRIC # (4)!
```

## Cloudvision preps
Add static routes to each students mgmt subnet using their vm as nexthop. 
```bash
ip route add 10.10.10.0/24 via 94.26.25.57 dev eth0
```
Login with the ansible user, or student user. 

Add devices


## Netbox playbooks, jinja templates and scripts

In this section we will prepare a series of playbooks, accompanied with jinja templates and python scripts. We will do all the exercises together, in plenum. This workbook is not considered a complete guide, it needs to be done together with the instructor.\

Previously we configured AVD "statically". Now we are going to update our AVD group_var files and inventory.yml to become a bit more dynamic. Meaning the configuration files in AVD no longer uses static values but get dynamic values from some other input, in this example Netbox. Therefore there are some preparatins we need to do for AVD to handle this.\
First of is installing some additional pip modules for our coming Python scripts. PS, make sure that the previous pip modules earlier have been installed in our python environment. I will go through that. Below is some additional pip modules that needs to be installed.  

Install the following python modules, (if unsure which check scripts for their dependencies) first script needs these:
```bash
(ci_cd_env) nlab@nlab-101:~/ci_cd_1/single-dc-l3ls/scripts$ pip install pynetbox requests colorama ipaddress
```

All the playbooks depend on the netbox_env.sh file with the following content:
```bash
# netbox_env.sh
export NETBOX_URL="http://localhost"
export NETBOX_TOKEN="3388e839465c444ddce04c69a9968fd63473a251"
export CVP_HOST="94.26.25.51"
export CVP_USER="ansible"
export CVP_PASSWORD="nlabpassword"
```
Update accordingly. This file is placed in the root of your avd repo single-dc-l3ls folder.

Next up is some preparations in Netbox. This can be done two ways, via the Netbox ui or via a script. 

To prepare Netbox for the first import:
1. Add device roles: l3leaf, l2leaf and spine
2. Add Manufacturers : Arista
3. Add Device Type : cEOSLab
4. Add Platform: eos
5. Add Device: name -> stx-dc1-xx, site: DC1, role: l3/l2leaf/spine, Type: cEOSLab, platform: eos. 

Or just run script called 01-create-basic-device.py

The scripts are found in this repo. Again, we will go through these together in plenum - step by step.\

Earlier we did delete the folders "documentation" and "intended". If this has not been done, make sure we have deleted  unwanted structured config files here (all files not starting with our famous "STx" prefix)::
```bash
(ci_cd_env) nlab@nlab-101:~/ci_cd_1/single-dc-l3ls/intended$ cd structured_configs/
(ci_cd_env) nlab@nlab-101:~/ci_cd_1/single-dc-l3ls/intended/structured_configs$ ls
cvp             dc1-leaf1b.yml  dc1-leaf2a.yml  dc1-leaf2c.yml  dc1-spine2.yml      st1-dc1-leaf1b.yml  st1-dc1-leaf2a.yml  st1-dc1-leaf2c.yml  st1-dc1-spine2.yml
dc1-leaf1a.yml  dc1-leaf1c.yml  dc1-leaf2b.yml  dc1-spine1.yml  st1-dc1-leaf1a.yml  st1-dc1-leaf1c.yml  st1-dc1-leaf2b.yml  st1-dc1-spine1.yml
```

One should only have the st1-dc1.... files and the cvp folder. Like this:

```bash
(ci_cd_env) nlab@nlab-101:~/ci_cd_1/single-dc-l3ls/intended/structured_configs$ rm dc1-*
(ci_cd_env) nlab@nlab-101:~/ci_cd_1/single-dc-l3ls/intended/structured_configs$ ll
total 84
drwxrwxr-x 3 nlab nlab  4096 Mar 11 12:20 ./
drwxrwxr-x 4 nlab nlab  4096 Mar 11 07:29 ../
drwxrwxr-x 2 nlab nlab  4096 Mar 11 09:48 cvp/
-rw-rw-r-- 1 nlab nlab 10713 Mar 11 11:38 st1-dc1-leaf1a.yml
-rw-rw-r-- 1 nlab nlab 10713 Mar 11 11:38 st1-dc1-leaf1b.yml
-rw-rw-r-- 1 nlab nlab  2468 Mar 11 11:38 st1-dc1-leaf1c.yml
-rw-rw-r-- 1 nlab nlab 10722 Mar 11 11:38 st1-dc1-leaf2a.yml
-rw-rw-r-- 1 nlab nlab 10724 Mar 11 11:38 st1-dc1-leaf2b.yml
-rw-rw-r-- 1 nlab nlab  2468 Mar 11 11:38 st1-dc1-leaf2c.yml
-rw-rw-r-- 1 nlab nlab  4967 Mar 11 11:38 st1-dc1-spine1.yml
-rw-rw-r-- 1 nlab nlab  4969 Mar 11 11:38 st1-dc1-spine2.yml
```

The scripts are either copy paste from this git repo, or the whole repo is cloned by using the following command:
```bash
git clone git@github.com:andreasm80/arista-automation-workshop.git
```
Note that this will create a folder automatically based on the name of the repository.\
My recommendation is to go to your home folder, then run the command above. From there we can copy the scripts as needed.\

I have create a script that prompts for certain needed fields to be updated in some of the templates. Again this is our popular STx prefixes. Even after this script has run, we still need the template with some minor changes as the script is not clever enough to take it all. We will go through that. Below is the script, it will also be located in the avd_playbooks/templates folder in this repo:
```bash
#!/usr/bin/env python3
import sys
import re

def read_template(filename):
    """Read the template file and return its contents."""
    try:
        with open(filename, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

def find_group_matches(template_content, base_groups):
    """Find full group names that end with the base group names, allowing any prefix."""
    group_matches = {}
    for group in base_groups:
        # Match any prefix followed by the exact group name as a whole word
        pattern = rf'\b\w*_{re.escape(group)}\b|\b{re.escape(group)}\b'
        matches = set(re.findall(pattern, template_content))
        # Include only matches that end with the base group name
        full_matches = {match for match in matches if match.endswith(group)}
        if full_matches:
            group_matches[group] = full_matches
        else:
            group_matches[group] = {group}  # Default to original if no matches
    return group_matches

def find_mgmt_gateway(template_content):
    """Find the mgmt_gateway line and its current value."""
    pattern = r'mgmt_gateway:\s*(\S+)'
    match = re.search(pattern, template_content)
    if match:
        return match.group(0), match.group(1)  # Full line, current IP
    return None, None

def main():
    # Check if filename is provided
    if len(sys.argv) != 2:
        print("Usage: python script.py <template_filename>")
        sys.exit(1)

    filename = sys.argv[1]

    # Read the original template
    original_template = read_template(filename)

    # Print the original template for debugging
    print("Original template:")
    print("-" * 50)
    print(original_template)
    print("-" * 50)

    # Base group names to look for
    base_groups = ["FABRIC", "DC1", "DC1_SPINES", "DC1_L3_LEAVES", "DC1_L2_LEAVES", "DC1_L3_LEAF", "DC1_L2_LEAF"]

    # Find all matching group names in the template
    group_matches = find_group_matches(original_template, base_groups)

    # Dictionary to store replacements
    replacements = {}

    # Prompt for new group names
    print("Enter new names for each group (press Enter to keep original name):")
    for base_group, matched_groups in group_matches.items():
        print(f"\nFound these variations for {base_group}: {', '.join(matched_groups)}")
        for matched_group in matched_groups:
            new_name = input(f"New name for {matched_group} [{matched_group}]: ").strip()
            if new_name:
                replacements[matched_group] = new_name

    # Prompt for new mgmt_gateway IP
    mgmt_gateway_line, current_ip = find_mgmt_gateway(original_template)
    if mgmt_gateway_line:
        new_ip = input(f"\nFound mgmt_gateway: {current_ip}. Enter new IP address [{current_ip}]: ").strip()
        if new_ip:
            replacements[mgmt_gateway_line] = f"mgmt_gateway: {new_ip}"

    # Create the modified template with exact replacements
    modified_template = original_template
    for old_name, new_name in replacements.items():
        pattern = rf'\b{re.escape(old_name)}\b'
        modified_template = re.sub(pattern, new_name, modified_template)

    # Print the modified template
    print("\nModified template:")
    print("-" * 50)
    print(modified_template)

    # Optionally save to file
    save = input("\nWould you like to save this to a file? (y/n): ").lower()
    if save == 'y':
        output_filename = input("Enter output filename: ")
        try:
            with open(output_filename, 'w') as f:
                f.write(modified_template)
            print(f"Template saved to {output_filename}")
        except Exception as e:
            print(f"Error saving file: {e}")

if __name__ == "__main__":
    main()
```

This script is excecuted against our two jinja templates: "inventory.yml.j2" and "update_dc1.j2". 
This is the way to run the script:

```bash
python rename_avd_constucts.py inventory.yml.j2
python rename_avd_constucts.py update_dc1.j2
```
 

Run first script to import all configured eos devices by AVD:\
1-import_devices_from_structured_config.py

Then if that succeeds, run the second script:\
2-import_vlan_site_assign_prefix_good.py

And if that succeeds, run the script to arange cabling and connections for the topology view plugin:\
5-create_cabling_connections_perfect.py


## Netbox and Ansible Playbooks - before we are getting into automated workflows

Now it is time to prepare the playbooks for manual operation. One playbook at a time. The following playbooks will be used:

1. 1-playbook-update_inventory.yml
2. 2-playbook-update_dc1_yml_according_to_inventory.yml
3. 3-playbook-update_network_services.yml
4. 4-playbook-update_connected_endpoints.yml

These playbooks are depending on the jinja templates in the folder templates under avd_playbooks and scripts/ under same folder.\
The python script update_inventory.yml can be copied to the scripts folder in your avd repo folder single-dc-l3ls.
 
The playbooks also depend on the netbox_env.sh file with the following content:
```bash
# netbox_env.sh
export NETBOX_URL="http://localhost"
export NETBOX_TOKEN="3388e839465c444ddce04c69a9968fd63473a251"
export CVP_HOST="94.26.25.51"
export CVP_USER="ansible"
export CVP_PASSWORD="nlabpassword"
```
Update accordingly. This file is placed in the root of your avd repo single-dc-l3ls folder.


When its time to run the first playbook, the template for update inventory: inventory.yml.j2 must be changed accordingly, eg: FABRIC to ST1_FABRIC etc..

```yaml
---
all:
  children:
    CLOUDVISION:
      hosts:
        cvp:
          ansible_host: {{ cvp_host }}
          ansible_httpapi_host: {{ cvp_host }}
          ansible_user: {{ cvp_user }}
          ansible_password: {{ cvp_password }}
          ansible_connection: httpapi
          ansible_httpapi_use_ssl: true
          ansible_httpapi_validate_certs: false
          ansible_network_os: eos
          ansible_httpapi_port: 443
          ansible_python_interpreter: $(which python3)
    ST1_FABRIC:
      children:
        ST1_DC1:
          vars:
            mgmt_gateway: 172.18.100.2
          children:
            ST1_DC1_SPINES:
              hosts:{% for spine in spines %}
                {{ spine.name }}:
                  ansible_host: {{ spine.ip }}{% endfor %}
            ST1_DC1_L3_LEAVES:
              hosts:{% for leaf in l3_leaves %}
                {{ leaf.name }}:
                  ansible_host: {{ leaf.ip }}{% endfor %}
            ST1_DC1_L2_LEAVES:
              hosts:{% for leaf in l2_leaves %}
                {{ leaf.name }}:
                  ansible_host: {{ leaf.ip }}{% endfor %}

    NETWORK_SERVICES:
      children:
        ST1_DC1_L3_LEAVES:
        ST1_DC1_L2_LEAVES:
    CONNECTED_ENDPOINTS:
      children:
        ST1_DC1_L3_LEAVES:
        ST1_DC1_L2_LEAVES:
```

If playbook 1 succeeds, next playbook is 2-playbook-update_dc1_yml_according_to_inventory.yml.
This playbook is dependent on the template "update_dc1.j2" which should be placed under /templates. 

This should be straight forward as it only updated the DC1.yml according to the inventory.yml.
ansible-playbook 2-playbook-update_dc1_yml_according_to_inventory.yml
BUT, one has to change the name of the DC1.yml file in the playbook:
```bash
TASK [Read existing DC1.yml] *************************************************************************************************************************************************
fatal: [localhost]: FAILED! => {"changed": false, "msg": "file not found: group_vars/DC1.yml"}
```

See example:
```yaml
---
- name: Update DC1.yml based on inventory.yml
  hosts: localhost
  gather_facts: no
  vars:
    inventory_file: "inventory.yml"
    dc1_file: "group_vars/ST1_DC1.yml"

  tasks:
    - name: Read inventory.yml
      ansible.builtin.slurp:
        src: "{{ inventory_file }}"
      register: inventory_content

    - name: Read existing ST1_DC1.yml
      ansible.builtin.slurp:
        src: "{{ dc1_file }}"
      register: dc1_content

    - name: Process inventory and update DC1 configuration
      ansible.builtin.template:
        src: templates/update_dc1.j2
        dest: "{{ dc1_file }}"
        mode: '0644'
        backup: no
      vars:
        inventory_data: "{{ inventory_content.content | b64decode | from_yaml }}"
        current_dc1: "{{ dc1_content.content | b64decode | from_yaml }}"
```
AND also update the template accordingly:

```yaml
---
mgmt_interface: Management0
mgmt_interface_description: oob_management

spine:
  defaults:
    platform: cEOS-lab
    loopback_ipv4_pool: 10.255.0.0/27
    bgp_as: 65100
  nodes:
{%- for host in inventory_data.all.children.ST1_FABRIC.children.ST1_DC1.children.ST1_DC1_SPINES.hosts | dict2items %}

    - name: {{ host.key }}
      id: {{ loop.index }}
      mgmt_ip: "{{ '{{ ansible_host }}/24' }}"
{%- endfor %}

l3leaf:
  defaults:
    platform: cEOS-lab
    loopback_ipv4_pool: 10.255.0.0/27
    loopback_ipv4_offset: 2
    vtep_loopback_ipv4_pool: 10.255.1.0/27
    uplink_interfaces: ['Ethernet1', 'Ethernet2']
    uplink_switches: ['st1-dc1-spine1', 'st1-dc1-spine2']
    uplink_ipv4_pool: 10.255.255.0/26
    mlag_peer_ipv4_pool: 10.255.1.64/27
    mlag_peer_l3_ipv4_pool: 10.255.1.96/27
    virtual_router_mac_address: 00:1c:73:00:00:99
    spanning_tree_priority: 4096
    spanning_tree_mode: mstp
  node_groups:
{%- set l3_leaves = inventory_data.all.children.ST1_FABRIC.children.ST1_DC1.children.ST1_DC1_L3_LEAVES.hosts | dict2items -%}
{%- set leaf_groups = {} -%}
{%- for leaf in l3_leaves -%}
  {%- set leaf_name = leaf.key -%}
  {%- set group_num = leaf_name | regex_replace('^(st1-dc1-leaf)(\\d+)([ab])$', '\\2') | int -%}
  {%- set group_name = 'ST1_DC1_L3_LEAF' ~ group_num -%}
  {%- if group_name not in leaf_groups -%}
    {%- do leaf_groups.update({group_name: {'nodes': [], 'bgp_as': 65100 + group_num}}) -%}
  {%- endif -%}
  {%- do leaf_groups[group_name].nodes.append({'name': leaf_name, 'ansible_host': leaf.value.ansible_host}) -%}
{%- endfor %}
{%- for group_name, group_data in leaf_groups.items() %}

    - group: {{ group_name }}
      bgp_as: {{ group_data.bgp_as }}
      nodes:
{%- set group_index = group_name | regex_replace('^ST1_DC1_L3_LEAF(\\d+)$', '\\1') | int -%}
{%- for node in group_data.nodes | sort(attribute='name') %}

        - name: {{ node.name }}
          id: {{ (group_index - 1) * 2 + loop.index }}
          mgmt_ip: "{{ '{{ ansible_host }}/24' }}"
          uplink_switch_interfaces:
            - Ethernet{{ (group_index - 1) * 2 + loop.index }}
            - Ethernet{{ (group_index - 1) * 2 + loop.index }}
{%- endfor %}
{%- endfor %}

l2leaf:
  defaults:
    platform: cEOS-lab
    spanning_tree_mode: mstp
  node_groups:
{%- set l2_leaves = inventory_data.all.children.ST1_FABRIC.children.ST1_DC1.children.ST1_DC1_L2_LEAVES.hosts | dict2items -%}
{%- set l2_groups = {} -%}
{%- for leaf in l2_leaves -%}
  {%- set leaf_name = leaf.key -%}
  {%- set group_num = leaf_name | regex_replace('^(st1-dc1-leaf)(\\d+)(c)$', '\\2') | int -%}
  {%- set group_name = 'ST1_DC1_L2_LEAF' ~ group_num -%}
  {%- if group_name not in l2_groups -%}
    {%- do l2_groups.update({group_name: {'nodes': [], 'uplink_switches': ['st1-dc1-leaf' ~ group_num ~ 'a', 'st1-dc1-leaf' ~ group_num ~ 'b']}}) -%}
  {%- endif -%}
  {%- do l2_groups[group_name].nodes.append({'name': leaf_name, 'ansible_host': leaf.value.ansible_host}) -%}
{%- endfor %}
{%- for group_name, group_data in l2_groups.items() %}

    - group: {{ group_name }}
      uplink_switches: {{ group_data.uplink_switches }}
      nodes:
{%- set group_index = group_name | regex_replace('^ST1_DC1_L2_LEAF(\\d+)$', '\\1') | int -%}
{%- for node in group_data.nodes %}

        - name: {{ node.name }}
          id: {{ group_index }}
          mgmt_ip: "{{ '{{ ansible_host }}/24' }}"
          uplink_switch_interfaces:
            - Ethernet6
            - Ethernet6
{%- endfor %}
{%- endfor %}
```

Next up is the the playbook 3, 3-playbook-update_network_services.yml.\
Before this playbook can be executed, we must make sure the VLANs have been added with their correct role. L2 vs L3. First create the role under Prefix & VLAN Roles, then assign the role to the VLANs in Netbox.
This playbook is also dependent on the template network_services.j2

```yaml
---
tenants:
  - name: "TENANT1"
    mac_vrf_vni_base: 10000
    vrfs:
{% set unique_vrfs = [] %}
{% for prefix in prefix_list %}
{% if prefix.vrf is defined and prefix.vrf.name not in unique_vrfs %}
{% set vrf = vrf_list | selectattr('id', 'equalto', prefix.vrf.id) | first | default({'name': 'default', 'custom_fields': {'vrf_vni': 1}}) %}
{% do unique_vrfs.append(vrf.name) %}
      - name: {{ vrf.name }}
        vrf_vni: {{ vrf.custom_fields.vrf_vni | default(vrf.id) }}
        vtep_diagnostic:
          loopback: {{ vrf.custom_fields.vrf_vni | default(vrf.id) }}
          loopback_ip_range: 10.255.{{ vrf.custom_fields.vrf_vni | default(vrf.id) }}.0/27
        svis:
{% for vlan in vlan_list if vlan.role.name == 'L3' %}
{% set matching_prefix = prefix_list | selectattr('vlan.id', 'equalto', vlan.id) | first | default({}) %}
{% if matching_prefix.vrf is defined and matching_prefix.vrf.name == vrf.name %}
{% set vlan_interfaces = interface_list | selectattr('name', 'match', 'Vlan' + vlan.vid|string) | list %}
{% set vlan_anycast_ips = ip_list | selectattr('assigned_object_id', 'in', vlan_interfaces | map(attribute='id') | list) | selectattr('role.value', 'equalto', 'anycast') | list %}
{% set devices_with_ip = vlan_anycast_ips | map(attribute='assigned_object.device.name') | unique | list %}
{% set all_l3leaf_count = l3leaf_devices | length %}
{% set devices_with_ip_count = devices_with_ip | length %}
          - id: {{ vlan.vid }}
            name: {{ vlan.name | default('VLAN_' ~ vlan.vid) }}
            enabled: true
{% if devices_with_ip_count == all_l3leaf_count and devices_with_ip_count > 0 %}
            ip_address_virtual: {{ (vlan_anycast_ips | first).address }}
{% elif devices_with_ip_count > 0 %}
            nodes:
{% for ip in vlan_anycast_ips %}
{% if ip.assigned_object.device.name in l3leaf_devices | map(attribute='name') %}
              - node: {{ ip.assigned_object.device.name }}
                ip_address: {{ ip.address }}
{% endif %}
{% endfor %}
{% endif %}
{% endif %}
{% endfor %}
{% endif %}
{% endfor %}
    l2vlans:
{% for vlan in vlan_list if vlan.role.name == 'L2' %}
      - id: {{ vlan.vid }}
        name: {{ vlan.name | default('VLAN_' ~ vlan.vid) }}
{% endfor %}
```
 
When Playbook3 has run succesfully it is time for playbook 4,  4-playbook-update_connected_endpoints.yml.
This playbook is dependent on the template connected_endpoints.j2. This playbook is also dependent on the tag "endpoint" and merged. These two tags are assigned to the ethernet interfaces that needs vlan defined. If the two tags are combined (same interface has both endpoint and merged tag), they are equally configured on two switches, typically a leaf pair.  

Playbook 4, 4-playbook-update_connected_endpoints.yml
```yaml
---
- name: Update CONNECTED_ENDPOINTS.yml from NetBox for dc1 site endpoints
  hosts: localhost
  gather_facts: no

  tasks:
    # Task 0: Load environment variables from netbox_env.sh
    - name: Parse netbox_env.sh into environment variables
      ansible.builtin.set_fact:
        env_vars: "{{ parsed_env }}"
      vars:
        parsed_env: "{{ dict(lookup('file', playbook_dir + '/netbox_env.sh') | split('\n') | select('match', '.*=.*') | map('regex_replace', '^export\\s+([^=]+)=\"([^\"]+)\"$', '\\1=\\2') | map('split', '=') | list) }}"

    # Task 1: Set environment for playbook
    - name: Set environment for playbook
      ansible.builtin.set_fact:
        netbox_url: "{{ env_vars.NETBOX_URL }}/api"
        netbox_token: "{{ env_vars.NETBOX_TOKEN }}"
        avd_group_vars_dir: "{{ playbook_dir }}/group_vars"
        site_slug: "dc1"

    # Task 2: Get all devices in the dc1 site
    - name: Fetch devices from NetBox for site dc1
      ansible.builtin.uri:
        url: "{{ netbox_url }}/dcim/devices/?site={{ site_slug }}"
        method: GET
        headers:
          Authorization: "Token {{ netbox_token }}"
          Accept: "application/json"
        return_content: yes
      register: netbox_devices

    # Debug devices
    - name: Debug fetched devices
      ansible.builtin.debug:
        var: netbox_devices.json.results
      when: netbox_devices.json.results is defined

    # Task 3: Fetch interfaces with tag "endpoint" for all devices
    - name: Fetch interfaces with tag "endpoint" for all devices
      ansible.builtin.uri:
        url: "{{ netbox_url }}/dcim/interfaces/?device={{ item.name }}&tag=endpoint"
        method: GET
        headers:
          Authorization: "Token {{ netbox_token }}"
          Accept: "application/json"
        return_content: yes
      loop: "{{ netbox_devices.json.results | default([]) }}"
      register: netbox_interfaces_per_device
      when: netbox_devices.json.results is defined and netbox_devices.json.results | length > 0
      no_log: true

    # Task 4: Collect adapter data
    - name: Initialize raw_adapters
      ansible.builtin.set_fact:
        raw_adapters: []

    - name: Collect adapter data from interfaces
      ansible.builtin.set_fact:
        raw_adapters: "{{ raw_adapters + [adapter_data] }}"
      loop: "{{ netbox_interfaces_per_device.results | default([]) | map(attribute='json') | map(attribute='results') | flatten }}"
      loop_control:
        loop_var: interface
      when:
        - interface.tags | selectattr('slug', 'equalto', 'endpoint') | list | length > 0
      vars:
        vlan_list: "{{ interface.tagged_vlans | map(attribute='vid') | list }}"
        vlan_string: "{{ vlan_list | join(',') }}"
        port_number: "{{ raw_adapters | default([]) | selectattr('name', 'equalto', interface.description) | length + 1 }}"
        adapter_data:
          name: "{{ interface.description }}"
          merge_group: "{{ 'merged' if interface.tags | selectattr('slug', 'equalto', 'merged') | list | length > 0 else interface.id }}"
          endpoint_port: "PCI{{ port_number }}"
          switch_port: "{{ interface.name }}"
          switch: "{{ interface.device.name }}"
          vlans: "{{ vlan_string if vlan_string else interface.untagged_vlan.vid | default('') }}"
          mode: "{{ 'trunk' if interface.tagged_vlans else 'access' }}"
          native_vlan: "{{ interface.untagged_vlan.vid | default('') if interface.tagged_vlans and interface.untagged_vlan else '' }}"

    # Debug collected raw adapters
    - name: Debug raw adapters
      ansible.builtin.debug:
        var: raw_adapters

    # Task 5: Group and merge adapters
    - name: Initialize endpoint_dict
      ansible.builtin.set_fact:
        endpoint_dict: {}

    - name: Group and merge adapters
      ansible.builtin.set_fact:
        endpoint_dict: "{{ endpoint_dict | combine({ item.0: {'adapters': grouped_adapters, 'name': item.1[0].name} }) }}"
      loop: "{{ raw_adapters | default([]) | groupby('merge_group') }}"
      vars:
        grouped_adapters:
          - endpoint_ports: "{{ item.1 | map(attribute='endpoint_port') | list }}"
            switch_ports: "{{ item.1 | map(attribute='switch_port') | list }}"
            switches: "{{ item.1 | map(attribute='switch') | list }}"
            vlans: "{{ item.1[0].vlans }}"
            mode: "{{ item.1[0].mode }}"
            native_vlan: "{{ item.1[0].native_vlan | default(omit) }}"

    # Debug grouped adapters
    - name: Debug grouped adapters
      ansible.builtin.debug:
        var: endpoint_dict

    # Task 6: Convert aggregated data to list
    - name: Convert aggregated data to list
      ansible.builtin.set_fact:
        new_endpoints: "{{ endpoint_dict | dict2items | map(attribute='value') | list }}"

    # Debug transformed endpoint list
    - name: Debug transformed endpoint list
      ansible.builtin.debug:
        var: new_endpoints

    # Task 7: Render CONNECTED_ENDPOINTS.yml with NetBox data
    - name: Render CONNECTED_ENDPOINTS.yml with NetBox data
      ansible.builtin.template:
        src: "templates/connected_endpoints.j2"
        dest: "{{ avd_group_vars_dir }}/CONNECTED_ENDPOINTS.yml"
        mode: '0644'
      vars:
        servers: "{{ new_endpoints | default([]) }}"

    # Task 8: Validate the YAML syntax
    - name: Validate updated YAML
      ansible.builtin.command: "yamllint {{ avd_group_vars_dir }}/CONNECTED_ENDPOINTS.yml"
      register: yaml_validation
      failed_when: yaml_validation.rc != 0 and 'error' in yaml_validation.stdout and 'empty-lines' not in yaml_validation.stdout
```

connected_endpoints.j2 template:
```yaml
---
# Definition of connected endpoints in the fabric.
servers:
{% for server in servers %}
  - name: {{ server.name }}
    adapters:
{% for adapter in server.adapters %}
      - endpoint_ports: {{ adapter.endpoint_ports | to_json }}
        switch_ports: {{ adapter.switch_ports | to_json }}
        switches: {{ adapter.switches | to_json }}
        vlans: "{{ adapter.vlans }}"
        mode: {{ adapter.mode }}
{% if adapter.native_vlan is defined and adapter.native_vlan != '' %}
        native_vlan: {{ adapter.native_vlan }}
{% endif %}
{% endfor %}
{% endfor %}
```

## Github Actions or Gitea Actions - Workflow:
We need to make git "work" for us based on workflows. These are operations being performed when something is done on certain actions in the repo. Like checking out a branch, merging or pull requests into main. 
Below is the workflows we are going to use in this workshop.\
The first workflow will start when we are checking out a branch. The second will start when merging into main. 

Workflow 1 (I have commented out some of the tasks as we are not able to perform these in our labs):
```yaml
name: 'CI Runner ansible build - all except main'

on:
  push:
    branches:
      - '*'
      - '!main' 
    paths:
      - 'group_vars/*'

#  pull_request:
#    branches:
#      - 'main'  # Only trigger on PRs to `main`
#    paths:
#      - 'group_vars/*'

jobs:

  run-avd-build:
    runs-on: ubuntu-latest
#    if: github.ref != 'refs/heads/main'
    container: 
      image: "registry.guzware.net/avd/avd-5.2:v2"

    steps:


#      - name: Install Ansible
#        run: pip install "pyavd[ansible]"

#      - name: Install Arista AVD
#        run: ansible-galaxy collection install arista.avd

      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Build Dev Configurations and Documentation
        run: |
          . /workspace/ansible-venv/bin/activate 
          ansible-playbook -i inventory.yml build.yml
#          ansible-playbook -i dev-inventory.yml build.yml

#      - name: Deploy to Dev digital-twin
#        run: |
#          . /workspace/ansible-venv/bin/activate
#          ansible-playbook -i dev-inventory.yml deploy.yml

#      - name: Run Automated Network Testing in Dev
#        run: |
#          . /workspace/ansible-venv/bin/activate
#          ansible-playbook -i dev-inventory.yml anta.yml

      - name: Commit and Push Generated Files
        run: |
          # Make sure any generated files are added to Git
          if [ -d "documentation" ]; then
            git add documentation/
          fi

          if [ -d "intended" ]; then
            git add intended/
          fi

          if [ -d "reports" ]; then
            git add reports/
          fi

          git config user.name "gitea-runner"
          git config user.email "user@mail.com"
          # Get the current branch name dynamically
          CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
          git commit -s -m "Update generated files from branch $CURRENT_BRANCH" || echo "No changes to commit"

          # Push changes to the current branch
          git push origin $CURRENT_BRANCH
```

The second workflow that acts on merge to main:
```yaml
name: 'CI Runner ansible deploy-cvp - in main'

on:
  push:
    branches:
      - 'main'
    paths:
      - 'group_vars/*'

jobs:

  run-avd-build:
    runs-on: ubuntu-latest
    container: 
      image: "registry.guzware.net/avd/avd-5.2:v2"

    steps:


#      - name: Install Ansible
#        run: pip install "pyavd[ansible]"

#      - name: Install Arista AVD
#        run: ansible-galaxy collection install arista.avd

      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Build Prod Configurations and Documentation
        run: |
          . /workspace/ansible-venv/bin/activate
          ansible-playbook -i inventory.yml build.yml

      - name: Commit and Push Generated Files
        run: |
          # Make sure any generated files are added to Git
          if [ -d "documentation" ]; then
            git add documentation/
          fi

          if [ -d "intended" ]; then
            git add intended/
          fi

          if [ -d "reports" ]; then
            git add reports/
          fi

          git config user.name "gitea-runner"
          git config user.email "andreas.marqvardsen@gmail.com"
          # Get the current branch name dynamically
          CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
          git commit -s -m "Update generated files from branch $CURRENT_BRANCH" || echo "No changes to commit"

          # Push changes to the current branch
          git push origin $CURRENT_BRANCH



      - name: Deploy changes to CloudVision
        run: |
          . /workspace/ansible-venv/bin/activate 
          ansible-playbook -i inventory.yml deploy-cvp.yml
```


## Netbox Jinja template config renderer. 

Remember the tags so the devices get the vlans "attached" for config render.

```yaml
! Arista EOS Configuration Generated by NetBox
hostname {{ device.name }}
{% if device.custom_field_data["name_server"] -%}
ip name-server vrf MGMT {{ device.custom_field_data["name_server"] }}
!
{% endif -%}
{% if device.custom_field_data["clock_timezone"] -%}
clock timezone {{ device.custom_field_data["clock_timezone"] }}
!
{% endif -%}
{%- for vlan in device.site.vlans.all() | sort(attribute='vid') -%}
{%- set has_device_tag = device.name in (vlan.tags.all() | map(attribute='slug')) -%}
{%- if vlan.site.slug == 'dc1' and has_device_tag %}
vlan {{ vlan.vid }}
   name {{ vlan.name }}{%- if "mlag" in vlan.name | lower %}
   trunk group MLAG{%- endif %}
!
{%- endif -%}
{%- endfor -%}
{%- if device.site.vlans.all() | selectattr('site.slug', '==', 'dc1') | selectattr('tags', 'defined') | list | length > 0 %}
 
{%- endif -%}
{%- set relevant_vrfs = [] -%}
{%- for interface in device.interfaces.all() -%}
{%- if interface.vrf and interface.vrf not in relevant_vrfs -%}
{%- set _ = relevant_vrfs.append(interface.vrf) -%}
{%- endif -%}
{%- endfor -%}
{%- for vrf in relevant_vrfs %}
vrf instance {{ vrf.name }}
!
{%- endfor -%}
{%- if relevant_vrfs %}
{%- endif -%}
{%- for interface in device.interfaces.all() %}
interface {{ interface.name }}
{%- if interface.description %}
   description {{ interface.description }}
{%- endif %}
{%- if interface.vrf %}
   vrf {{ interface.vrf.name }}
{%- endif %}
{%- if interface.mtu %}
   mtu {{ interface.mtu }}
{%- endif %}
{%- if interface.mode == "access" and interface.untagged_vlan %}
   switchport mode access
   switchport access vlan {{ interface.untagged_vlan.vid }}
{%- elif interface.mode == "tagged" %}
   switchport mode trunk
{%- if interface.untagged_vlan %}
   switchport trunk native vlan {{ interface.untagged_vlan.vid }}
{%- endif %}
{%- if interface.tagged_vlans.all() %}
   switchport trunk allowed vlan {% for vlan in interface.tagged_vlans.all() %}{{ vlan.vid }}{% if not loop.last %},{% endif %}{% endfor %}
{%- endif %}
{%- endif %}
{%- if interface.ip_addresses.all() %}
{%- for ip in interface.ip_addresses.all() %}
   ip address {{ ip.address }}
{%- endfor %}
{%- endif %}
!
{%- endfor -%}
{%- if device.role.slug == "switch" and device.vlans.all() %}
! VLAN Configuration
vlan database
{%- for vlan in device.vlans.all() %}
   vlan {{ vlan.vid }}
   name {{ vlan.name }}
{%- endfor %}
exit
!
{%- endif %}
end
```
 
