"""
This module contains tests for the gNOI System API.
"""
import pytest
import logging

from .helper import gnoi_request, extract_gnoi_response
from tests.common.helpers.assertions import pytest_assert

pytestmark = [
    pytest.mark.topology('any')
]


def test_gnoi_system_time(duthosts, rand_one_dut_hostname, localhost):
    """
    Verify the gNOI System Time API returns the current system time in valid JSON format.
    """
    duthost = duthosts[rand_one_dut_hostname]

    ret, msg = gnoi_request(duthost, localhost, "System", "Time", "")
    pytest_assert(ret == 0, "System.Time API reported failure (rc = {}) with message: {}".format(ret, msg))
    logging.info("System.Time API returned msg: {}".format(msg))

    # Message should contain a JSON substring like this {"time":1735921221909617549}
    msg_json = extract_gnoi_response(msg)
    if not msg_json:
        pytest.fail("Failed to extract JSON from System.Time API response")
    logging.info("Extracted JSON: {}".format(msg_json))
    pytest_assert("time" in msg_json, "System.Time API did not return time")
