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
