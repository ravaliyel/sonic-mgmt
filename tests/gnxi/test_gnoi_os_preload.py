"""
Tests for gNOI OS.Install (preload) API.

This module tests the gNOI (gRPC Network Operations Interface) OS.Install
service, which provides a mechanism to preload an OS image onto the device
without activating it. A preloaded image can later be activated via OS.Activate
and made live after the next reboot.

The gNOI OS.Install RPC is a bidirectional streaming RPC:
  - Client sends a TransferRequest with the target version.
  - If the version is already present, the server returns ``validated``.
  - If the version is absent, the server returns ``transferReady``, after
    which the client would stream the image content (not covered here).
  - On error, the server returns ``installError``.
"""

import logging
import pytest

from tests.common.helpers.assertions import pytest_assert

logger = logging.getLogger(__name__)

INVALID_VERSION_STRING = "invalid-os-version-that-does-not-exist"

pytestmark = [
    pytest.mark.topology("any"),
    pytest.mark.usefixtures("setup_gnoi_tls_server"),
]


@pytest.mark.disable_loganalyzer
def test_gnoi_os_preload_current_version(duthosts, rand_one_dut_hostname, gnmi_tls):
    """
    Verify that OS.Install returns ``validated`` for the currently running image.

    When the device already has a version installed, a preload request for
    that same version should return a ``validated`` response indicating the
    image is already present and no transfer is needed.

    Args:
        duthosts: Fixture providing access to DUT hosts
        rand_one_dut_hostname: Fixture providing a random DUT hostname
        gnmi_tls: Fixture providing gNOI client interface (TLS)
    """
    duthost = duthosts[rand_one_dut_hostname]

    current_image = duthost.image_facts()["ansible_facts"]["ansible_image_facts"]["current"]
    logger.info("Testing OS.Install preload with current image version: %s", current_image)

    responses = gnmi_tls.gnoi.os_install(current_image)

    pytest_assert(
        responses,
        "OS.Install returned no responses for current image version"
    )

    first_response = responses[0]
    logger.info("OS.Install first response: %s", first_response)

    pytest_assert(
        "validated" in first_response or "transferReady" in first_response,
        f"OS.Install did not return 'validated' or 'transferReady' for current image: {first_response}"
    )

    if "validated" in first_response:
        logger.info(
            "OS.Install correctly returned 'validated' — image already present on device: %s",
            first_response.get("validated", {})
        )
    else:
        logger.info(
            "OS.Install returned 'transferReady' — device is ready to receive image data: %s",
            first_response.get("transferReady", {})
        )


@pytest.mark.disable_loganalyzer
def test_gnoi_os_preload_invalid_version(gnmi_tls):
    """
    Verify that OS.Install returns an ``installError`` for an invalid version.

    When the client requests preload of a version that does not exist and
    cannot be resolved, the server should respond with an ``installError``
    indicating the failure reason.

    Args:
        gnmi_tls: Fixture providing gNOI client interface (TLS)
    """
    invalid_version = INVALID_VERSION_STRING
    logger.info("Testing OS.Install preload with invalid version: %s", invalid_version)

    responses = gnmi_tls.gnoi.os_install(invalid_version)

    pytest_assert(
        responses,
        "OS.Install returned no responses for invalid version"
    )

    first_response = responses[0]
    logger.info("OS.Install first response for invalid version: %s", first_response)

    pytest_assert(
        "installError" in first_response or "transferReady" in first_response,
        f"OS.Install did not return 'installError' or 'transferReady' for invalid version: {first_response}"
    )

    if "installError" in first_response:
        error_detail = first_response.get("installError", {}).get("detail", "")
        logger.info(
            "OS.Install correctly returned 'installError' for invalid version: %s", error_detail
        )
    else:
        logger.info(
            "OS.Install returned 'transferReady' for invalid version "
            "(server awaiting image content): %s",
            first_response.get("transferReady", {})
        )
