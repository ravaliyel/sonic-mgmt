
# tests/gnoi/test_gnoi_file_transfer_to_remote.py

import os
import subprocess
import json
import time

# Configurable knobs (could be pulled from pytest args/ansible vars later)
GNOI_CLIENT_CONTAINER = "gnoi-client"   # replace with actual container name
GNOI_CLIENT_BIN       = "/usr/bin/gmmi_client"  # replace if different
GNOI_TARGET           = "localhost:5500"        # adjust to your gRPC port
REMOTE_URL            = "http://<control-ip>:8000/dummy.txt"  # set at runtime
REMOTE_DEST_PATH      = "/tmp/dummy.txt"        # destination on DUT
LOCAL_TMP_PATH        = "/tmp"                  # local path used by RPC (if applicable)
TIMEOUT_SEC           = 60

def _build_request_json():
    """
    Build the JSON payload for GNOI file.transfer_to_remote as described in the meeting.
    Fields used: path, local_path, remote_download (URL).
    """
    req = {
        "path": REMOTE_DEST_PATH,
        "local_path": LOCAL_TMP_PATH,
        "remote_download": REMOTE_URL
    }
    return json.dumps(req)

def _docker_exec_gnoi(json_payload: str):
    """
    Execute the gmmi/gnoi client via docker exec, passing module=file and rpc=transfer_to_remote.
    Meeting guidance: docker exec <container> gmmi_client --target localhost:<port> --module file --rpc transfer_to_remote --json '<payload>'
    """
    cmd = [
        "docker", "exec", GNOI_CLIENT_CONTAINER,
        GNOI_CLIENT_BIN,
        "--target", GNOI_TARGET,
        "--module", "file",
        "--rpc", "transfer_to_remote",
        "--json", json_payload
    ]
    print("Running:", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SEC)

def test_gnoi_file_transfer_to_remote():
    # 1) Ensure test preconditions (e.g., environment variable for REMOTE_URL)
    url = os.environ.get("GNOI_REMOTE_URL", REMOTE_URL)
    assert url.startswith("http://") or url.startswith("https://"), "REMOTE_URL must be HTTP(S)"

    # 2) Build the request
    payload = _build_request_json().replace(REMOTE_URL, url)

    # 3) Call the client
    proc = _docker_exec_gnoi(payload)

    # 4) Basic checks on client output
    print("STDOUT:\n", proc.stdout)
    print("STDERR:\n", proc.stderr)
    assert proc.returncode == 0, f"GNOI client failed: {proc.stderr}"

    # 5) Optionally, verify the file landed on DUT (example via docker exec to DUT namespace)
    # Replace with a proper check command available in your environment.
    verify_cmd = ["docker", "exec", GNOI_CLIENT_CONTAINER, "bash", "-lc", f"ls -l {REMOTE_DEST_PATH} && wc -c {REMOTE_DEST_PATH}"]
    verify = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=TIMEOUT_SEC)
    print("VERIFY:\n", verify.stdout)
    assert verify.returncode == 0, f"Destination file not found: {verify.stderr}"
    # Optional: size > 0
    assert " 0 " not in verify.stdout, "Downloaded file appears empty"
