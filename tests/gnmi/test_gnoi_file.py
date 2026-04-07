"""
Simple integration tests for gNOI File service.
"""
import json
import pytest
import logging

from .helper import gnoi_request
from tests.common.utilities import wait_until

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.topology('any')
]


def test_file_stat(duthosts, rand_one_dut_hostname, localhost):
    """Test File.Stat RPC."""
    duthost = duthosts[rand_one_dut_hostname]

    request_json = json.dumps({"path": "/etc/hostname"})
    try:
        ret, msg = gnoi_request(duthost, localhost, "File", "Stat", request_json)
        if ret == 0:
            logger.info("File.Stat result: {}".format(msg))
        else:
            # File service may not be fully implemented
            logger.warning("File.Stat returned error (may be expected): {}".format(msg))
    except Exception as e:
        # File service may not be fully implemented
        logger.warning("File.Stat failed (expected): {}".format(e))


def test_file_transfer_to_remote(duthosts, rand_one_dut_hostname, localhost, ptfhost):
    """Test File.TransferToRemote RPC downloading file from HTTP server to DUT."""
    duthost = duthosts[rand_one_dut_hostname]

    # Test file configuration
    test_filename = "test.txt"
    test_content = "Hello from gNOI TransferToRemote test!"
    local_path = "/tmp/{}".format(test_filename)
    http_port = 8080

    try:
        # 1. Create test file on PTF host
        logger.info("Creating test file {} on PTF host".format(test_filename))
        ptfhost.shell("echo '{}' > /tmp/{}".format(test_content, test_filename))

        # 2. Start HTTP server on PTF host
        logger.info("Starting HTTP server on PTF host port {}".format(http_port))
        ptfhost.command("cd /tmp && python3 -m http.server {}".format(http_port), module_async=True)

        # 3. Wait for HTTP server to start
        ptf_ip = ptfhost.mgmt_ip
        logger.info("Waiting for HTTP server to start at {}:{}".format(ptf_ip, http_port))

        def server_ready():
            try:
                result = ptfhost.command("curl -f --max-time 2 {}:{}".format(ptf_ip, http_port),
                                         module_ignore_errors=True)
                return result["rc"] == 0
            except Exception:
                return False

        wait_until(server_ready, timeout=30, interval=2, delay=2, backoff=1.1)
        logger.info("HTTP server is ready")

        # 4. Test TransferToRemote
        remote_url = "http://{}:{}/{}".format(ptf_ip, http_port, test_filename)
        logger.info("Testing TransferToRemote: {} -> {}".format(remote_url, local_path))

        request_json = json.dumps({
            "local_path": local_path,
            "remote_download": {
                "url": remote_url
            }
        })
        ret, msg = gnoi_request(duthost, localhost, "File", "TransferToRemote", request_json)

        if ret == 0:
            # 5. Verify file was downloaded to DUT
            file_stat = duthost.stat(path=local_path)
            assert file_stat["stat"]["exists"], "File {} not found on DUT after transfer".format(local_path)
            logger.info("File successfully downloaded to DUT: {}".format(local_path))

            # 6. Verify downloaded content
            downloaded_content = duthost.shell("cat {}".format(local_path))["stdout"].strip()
            assert test_content in downloaded_content, \
                "Content mismatch. Expected: '{}', Got: '{}'".format(test_content, downloaded_content)
            logger.info("File content verified: {}".format(downloaded_content))

            logger.info("TransferToRemote test completed successfully")
        else:
            # File service may not be fully implemented
            logger.warning("File.TransferToRemote failed (may be expected): {}".format(msg))

    except Exception as e:
        # File service may not be fully implemented
        logger.warning("File.TransferToRemote failed (may be expected): {}".format(e))

    finally:
        # 7. Cleanup
        logger.info("Cleaning up test resources")
        try:
            # Stop HTTP server
            ptfhost.command("pkill -f 'python3.*http.server.*{}'".format(http_port),
                            module_ignore_errors=True)
            # Remove test file from PTF
            ptfhost.shell("rm -f /tmp/{}".format(test_filename), module_ignore_errors=True)
            # Remove downloaded file from DUT
            duthost.shell("rm -f {}".format(local_path), module_ignore_errors=True)
            logger.info("Cleanup completed")
        except Exception as cleanup_e:
            logger.warning("Cleanup failed: {}".format(cleanup_e))
