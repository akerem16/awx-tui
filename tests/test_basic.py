"""
Basic smoke tests for AWX TUI

Verifies package structure and imports work correctly.
"""


def test_package_imports():
    """Test that package can be imported"""
    import awx_tui

    assert awx_tui.__version__
    assert awx_tui.__author__


def test_rotating_names():
    """Test rotating application names exist"""
    from awx_tui import ROTATING_NAMES, TAGLINE

    assert len(ROTATING_NAMES) > 0
    assert "AWX TUI" in ROTATING_NAMES
    assert "Rage Tater" in ROTATING_NAMES[1]  # Second name contains "Rage Tater"
    assert TAGLINE
    assert "automation" in TAGLINE.lower()


def test_main_module_exists():
    """Test main module can be imported"""
    from awx_tui import main

    assert hasattr(main, "main")
    assert callable(main.main)


def test_config_classes_exist():
    """Test config dataclasses exist"""
    from awx_tui.config import InstanceConfig

    # Can create instances
    instance = InstanceConfig(
        name="test", url="https://test.example.com", auth_method="token", username="admin", token="test-token"
    )
    assert instance.name == "test"
    assert instance.verify_ssl is True  # Default value


def test_client_class_exists():
    """Test AWX client can be imported"""
    from awx_tui.client import AWXClient

    assert AWXClient


def test_mock_data_exists():
    """Test mock data structures exist"""
    from awx_tui.mock_data import MOCK_INSTANCES

    assert "mock-prod" in MOCK_INSTANCES
    assert "mock-dev" in MOCK_INSTANCES
    assert "mock-staging" in MOCK_INSTANCES


def test_app_class_exists():
    """Test Textual app class exists"""
    from awx_tui.app import AWXTUIApp

    assert AWXTUIApp


# More tests will be added as features are implemented
