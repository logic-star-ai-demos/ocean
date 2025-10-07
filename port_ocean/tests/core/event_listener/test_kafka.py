from port_ocean.core.event_listener.kafka import KafkaEventListenerSettings
import pytest
from pydantic import ValidationError


def test_default_kafka_settings() -> None:
    """Test default values are properly set"""
    config = KafkaEventListenerSettings(type="KAFKA")
    assert config.type == "KAFKA"
    assert config.security_protocol == "SASL_SSL"
    assert config.authentication_mechanism == "SCRAM-SHA-512"
    assert config.kafka_security_enabled is True
    assert config.consumer_poll_timeout == 1
    assert "b-1-public.publicclusterprod" in config.brokers


def test_brokers_json_array_parsing() -> None:
    """Test that JSON array strings get converted to comma-separated"""
    json_brokers = '["broker1:9092", "broker2:9092", "broker3:9092"]'
    config = KafkaEventListenerSettings(type="KAFKA", brokers=json_brokers)
    assert config.brokers == "broker1:9092,broker2:9092,broker3:9092"


def test_brokers_regular_string_unchanged() -> None:
    """Test that regular comma-separated strings pass through unchanged"""
    regular_brokers = "broker1:9092,broker2:9092"
    config = KafkaEventListenerSettings(type="KAFKA", brokers=regular_brokers)
    assert config.brokers == regular_brokers


def test_brokers_malformed_json_unchanged() -> None:
    """Test that malformed JSON strings don't break validation"""
    bad_json = "[broker1:9092, broker2:9092"
    config = KafkaEventListenerSettings(type="KAFKA", brokers=bad_json)
    assert config.brokers == bad_json


def test_custom_values() -> None:
    """Test overriding default values"""
    config = KafkaEventListenerSettings(
        type="KAFKA",
        brokers="custom:9092",
        security_protocol="PLAINTEXT",
        authentication_mechanism="PLAIN",
        kafka_security_enabled=False,
        consumer_poll_timeout=5,
    )
    assert config.brokers == "custom:9092"
    assert config.security_protocol == "PLAINTEXT"
    assert config.authentication_mechanism == "PLAIN"
    assert config.kafka_security_enabled is False
    assert config.consumer_poll_timeout == 5


def test_type_literal_validation() -> None:
    """Test that type field only accepts KAFKA"""
    with pytest.raises(ValidationError):
        KafkaEventListenerSettings(type="RABBITMQ")  # type: ignore[arg-type]


def test_empty_brokers_array() -> None:
    """Test empty JSON array becomes empty string"""
    config = KafkaEventListenerSettings(type="KAFKA", brokers="[]")
    assert config.brokers == ""


def test_single_broker_array() -> None:
    """Test single broker in JSON array"""
    config = KafkaEventListenerSettings(type="KAFKA", brokers='["single:9092"]')
    assert config.brokers == "single:9092"


def test_init_clients_accepts_json_string_cluster_conf_mapping(monkeypatch) -> None:
    """Kafka init_clients should accept cluster_conf_mapping provided as JSON string (GitHub secret).
    This test expects init_clients to parse JSON string into dict and return a KafkaClient list.
    The current implementation raises AttributeError; this test will fail until the bug is fixed."""
    import sys
    import os
    # Make sure the kafka_integration package is importable (it's located under integrations/kafka)
    sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), "integrations", "kafka")))

    # Prepare a fake Ocean app and initialize the global _port_ocean before importing integrations.kafka.main
    from port_ocean.context.ocean import PortOceanContext
    import port_ocean.context.ocean as ocean_module

    mapping_str = '{"clusterA": {"bootstrap.servers": "localhost:9092"}}'
    fake_integration_config = type("IC", (), {"config": mapping_str})()
    fake_event_listener = type("E", (), {"should_resync": True})()
    fake_config = type("C", (), {"integration": fake_integration_config, "event_listener": fake_event_listener})()
    fake_integration_obj = type("IntObj", (), {"on_resync": lambda self, function, kind: function, "on_start": lambda self, function: function, "on_resync_start": lambda self, function: function, "on_resync_complete": lambda self, function: function})()
    fake_app = type("A", (), {"config": fake_config, "integration": fake_integration_obj})()
    ocean_module._port_ocean = PortOceanContext(app=fake_app)

    # Now import the kafka integration module and patch KafkaClient to avoid external dependencies
    import integrations.kafka.main as kafka_main

    class DummyKafkaClient:
        def __init__(self, cluster_name, conf):
            self.cluster_name = cluster_name
            self.conf = conf

    monkeypatch.setattr(kafka_main, "KafkaClient", DummyKafkaClient)

    # Call the function under test. Expected behavior: parse JSON string and return clients list.
    clients = kafka_main.init_clients()
    assert isinstance(clients, list)
    assert len(clients) == 1
    assert clients[0].cluster_name == "clusterA"
    assert isinstance(clients[0].conf, dict)
    assert clients[0].conf.get("bootstrap.servers") == "localhost:9092"
