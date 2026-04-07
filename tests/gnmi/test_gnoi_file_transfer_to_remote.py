"""
Integration tests for gNOI File.TransferToRemote RPC.

All tests automatically run with TLS server configuration via the gnmi_tls fixture.
"""
import pytest
import logging

from tests.common.fixtures.grpc_fixtures import gnmi_tls  # noqa: F401

logger = logging.getLogger(__name__)

REMOTE_DEST_PATH = "/tmp/gnoi_transfer_test_file"

pytestmark = [
    pytest.mark.topology('any'),
]


def test_gnoi_file_transfer_to_remote(gnmi_tls, duthost, request):  # noqa: F811
    """Test File.TransferToRemote RPC downloads a remote file to the DUT."""
    remote_url = request.config.getoption("--gnoi_remote_url", default=None, skip=True)
    assert remote_url, (
        "A remote URL must be provided via --gnoi_remote_url pytest option "
        "(e.g. http://<server>/file.bin)"
    )
    assert remote_url.startswith("http://") or remote_url.startswith("https://"), (
        "remote_url must be an HTTP(S) URL"
    )

    logger.info("Calling gNOI File.TransferToRemote: url=%s dest=%s", remote_url, REMOTE_DEST_PATH)
    result = gnmi_tls.gnoi.file_transfer_to_remote(
        url=remote_url,
        local_path=REMOTE_DEST_PATH,
    )
    logger.info("TransferToRemote result: %s", result)

    # Verify the file exists on the DUT after the transfer
    stat_result = duthost.stat(path=REMOTE_DEST_PATH)
    assert stat_result["stat"]["exists"], f"File not found on DUT after transfer: {REMOTE_DEST_PATH}"
    assert stat_result["stat"]["size"] > 0, f"Downloaded file is empty: {REMOTE_DEST_PATH}"
    logger.info("File successfully transferred to DUT: %s (size=%d bytes)",
                REMOTE_DEST_PATH, stat_result["stat"]["size"])
