"""
Pytest configuration for gNXI tests.

Loads shared fixtures for gNOI/gNMI testing so individual test modules
do not need to declare ``pytest_plugins`` themselves.
"""
pytest_plugins = ["tests.common.fixtures.grpc_fixtures"]
