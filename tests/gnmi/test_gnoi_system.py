"""
This module contains tests for the gNOI System API.

All tests automatically run with TLS server configuration by default.
Users don't need to worry about TLS configuration.
"""
import pytest
import logging

from tests.common.fixtures.grpc_fixtures import gnmi_tls  # noqa: F401

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.topology('any')
]


def test_gnoi_system_time(gnmi_tls):  # noqa: F811
    """
    Verify the gNOI System Time API returns the current system time.
    """
    result = gnmi_tls.gnoi.system_time()
    assert "time" in result, "System.Time API did not return time"
    assert isinstance(result["time"], int), "System.Time API returned non-integer time"
    logger.info("System time: {} nanoseconds since epoch".format(result["time"]))
