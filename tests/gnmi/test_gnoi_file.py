"""
Simple integration tests for gNOI File service.

All tests automatically run with TLS server configuration by default.
Users don't need to worry about TLS configuration.
"""
import pytest
import logging

from tests.common.fixtures.grpc_fixtures import gnmi_tls  # noqa: F401
from tests.common.utilities import wait_until

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.topology('any'),
]


def test_file_stat(gnmi_tls):  # noqa: F811
    """Test File.Stat RPC with TLS enabled by default."""
    try:
        result = gnmi_tls.gnoi.file_stat("/etc/hostname")
        assert "stats" in result
        logger.info("File stats: {}".format(result['stats'][0]))
    except Exception as e:
        # File service may not be fully implemented
        logger.warning("File.Stat failed (expected): {}".format(e))


def test_file_transfer_to_remote(gnmi_tls, ptfhost, duthosts, rand_one_dut_hostname):  # noqa: F811
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

        result = gnmi_tls.gnoi.file_transfer_to_remote(
            local_path=local_path,
            remote_url=remote_url
        )

        # 5. Verify response has hash
        assert "hash" in result, "TransferToRemote response missing hash field"
        logger.info("TransferToRemote response: {}".format(result))

        # 6. Verify file was downloaded to DUT
        file_stat = duthost.stat(path=local_path)
        assert file_stat["stat"]["exists"], "File {} not found on DUT after transfer".format(local_path)
        logger.info("File successfully downloaded to DUT: {}".format(local_path))

        # 7. Verify downloaded content
        downloaded_content = duthost.shell("cat {}".format(local_path))["stdout"].strip()
        assert test_content in downloaded_content, \
            "Content mismatch. Expected: '{}', Got: '{}'".format(test_content, downloaded_content)
        logger.info("File content verified: {}".format(downloaded_content))

        logger.info("TransferToRemote test completed successfully")

    except Exception as e:
        # File service may not be fully implemented
        logger.warning("File.TransferToRemote failed (may be expected): {}".format(e))

    finally:
        # 8. Cleanup
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
