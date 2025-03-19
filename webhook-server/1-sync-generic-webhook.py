import subprocess
import os
import hmac
import hashlib
from flask import Flask, request, jsonify
from rich import print
from rich.console import Console
from datetime import datetime
import threading  # Added for background tasks

# Flask app setup
app = Flask(__name__)
console = Console()

# Webhook Configuration
WEBHOOK_SECRET = "GW7M3riaqoI9xzV4wHdTUdWGwrt3AcMQADZ0_qImQEI"

# Ansible and Git Configuration
ENV_FILE = "/home/andreasm/environment/netbox-env.sh"
REPO_PATH = "/home/andreasm/netbox_avd_integration"
PLAYBOOKS = [
    f"{REPO_PATH}/1-playbook-update_inventory.yml",
    f"{REPO_PATH}/2-playbook-update_dc1_yml_according_to_inventory.yml",
    f"{REPO_PATH}/3-playbook-update_network_services.yml",
    f"{REPO_PATH}/4-playbook-update_connected_endpoints.yml"
]

def run_ansible_playbooks():
    """Runs the list of Ansible playbooks in order."""
    for playbook in PLAYBOOKS:
        try:
            playbook_name = os.path.basename(playbook)
            print(f"[bold blue]🚀 Running Ansible Playbook: {playbook_name}[/bold blue]")
            command = f"source {ENV_FILE} && ansible-playbook {playbook}"

            result = subprocess.run(
                ["bash", "-c", command],
                cwd=REPO_PATH,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"[bold green]✔️ Playbook {playbook_name} executed successfully[/bold green]")
                console.print(f"[bold green]📜 {playbook_name} Output:[/bold green]", style="green")
                console.print(result.stdout, style="cyan")
            else:
                print(f"[bold red]❌ Playbook {playbook_name} failed:[/bold red] {result.stderr}")
                return False

        except subprocess.CalledProcessError as e:
            print(f"[bold red]❌ Error executing playbook {playbook_name}:[/bold red] {e.stderr}")
            return False
    return True

def create_branch_and_push():
    """Creates a new branch with date-time name, runs playbooks, commits changes, and pushes it."""
    branch_name = datetime.now().strftime("sync-%Y%m%d-%H%M%S")
    print(f"[bold blue]🔀 Preparing branch: {branch_name}[/bold blue]")

    try:
        os.chdir(REPO_PATH)

        # Check if there are uncommitted changes in main
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        if status_result.stdout.strip():
            print("[bold red]❌ Main branch has uncommitted changes. Please commit or stash them manually.[/bold red]")
            return False

        # Fetch latest updates from origin
        subprocess.run(["git", "fetch", "origin"], check=True)

        # Create and checkout new branch from main
        print(f"[bold green]✔️ Creating new branch: {branch_name}[/bold green]")
        subprocess.run(["git", "checkout", "-b", branch_name, "origin/main"], check=True)

        # Run all playbooks in order
        if not run_ansible_playbooks():
            print("[bold red]❌ One or more playbooks failed, aborting Git operations[/bold red]")
            subprocess.run(["git", "checkout", "main"], check=True)
            subprocess.run(["git", "branch", "-D", branch_name], check=True)
            return False

        # Add all changes
        subprocess.run(["git", "add", "."], check=True)

        # Commit changes if there are any
        commit_result = subprocess.run(
            ["git", "commit", "-m", f"Auto-sync triggered at {branch_name}"],
            capture_output=True,
            text=True
        )

        if "nothing to commit" in commit_result.stdout.lower():
            print(f"[bold yellow]⚠️ No changes detected, skipping push.[/bold yellow]")
            subprocess.run(["git", "checkout", "main"], check=True)
            subprocess.run(["git", "branch", "-D", branch_name], check=True)
            print(f"[bold green]✔️ Deleted branch '{branch_name}'[/bold green]")
            return False

        # Push changes
        print(f"[bold green]⬆️ Pushing branch: {branch_name} to remote[/bold green]")
        subprocess.run(["git", "push", "origin", branch_name], check=True)

        print(f"[bold green]✔️ Successfully pushed branch {branch_name}[/bold green]")
        subprocess.run(["git", "checkout", "main"], check=True)
        return True

    except subprocess.CalledProcessError as e:
        print(f"[bold red]❌ Git process failed: {e}[/bold red]")
        subprocess.run(["git", "checkout", "main"], check=True)
        return False

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    print("[bold blue]ℹ️ Webhook received...[/bold blue]")

    raw_data = request.get_data(as_text=True)
    try:
        data = request.get_json()
    except Exception as e:
        print(f"[bold red]❌ Error parsing JSON:[/bold red] {str(e)}")
        return jsonify({"error": "Invalid JSON"}), 400

    # Verify Webhook Secret
    received_secret = request.headers.get('X-Hook-Signature')
    expected_secret = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        raw_data.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()

    if not received_secret or received_secret != expected_secret:
        print("[bold red]❌ Invalid or missing webhook secret[/bold red]")
        return jsonify({"error": "Invalid or missing webhook secret"}), 403

    # Minimal validation
    if data.get('event') != "manual_sync":
        print("[bold red]❌ Invalid event type[/bold red]")
        return jsonify({"error": "Invalid event type"}), 400

    print(f"[bold blue]🔄 Processing manual sync triggered at {data.get('timestamp')}[/bold blue]")

    # Run the task in a background thread
    thread = threading.Thread(target=create_branch_and_push)
    thread.start()

    # Respond immediately
    return jsonify({"message": "Webhook received, processing started in the background"}), 202

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
