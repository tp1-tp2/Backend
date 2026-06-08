# Feature: asr-platform-backend, Task 1.6: Integration tests for Kubernetes configurations
import os
from pathlib import Path

import pytest
import yaml

K8S_ROOT = Path(__file__).parent.parent.parent / "k8s"
SERVICES = [
    "api-gateway",
    "auth-service",
    "user-service",
    "audio-processor",
    "asr-service",
    "transcription-manager",
]


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.mark.parametrize("service", SERVICES)
def test_deployment_manifest_exists(service: str):
    assert (K8S_ROOT / service / "deployment.yaml").exists()


@pytest.mark.parametrize("service", SERVICES)
def test_service_manifest_exists(service: str):
    assert (K8S_ROOT / service / "service.yaml").exists()


@pytest.mark.parametrize("service", SERVICES)
def test_hpa_manifest_exists(service: str):
    assert (K8S_ROOT / service / "hpa.yaml").exists()


@pytest.mark.parametrize("service", SERVICES)
def test_deployment_has_minimum_two_replicas(service: str):
    doc = load_yaml(K8S_ROOT / service / "deployment.yaml")
    assert doc["spec"]["replicas"] >= 2


@pytest.mark.parametrize("service", SERVICES)
def test_deployment_has_rolling_update_strategy(service: str):
    doc = load_yaml(K8S_ROOT / service / "deployment.yaml")
    assert doc["spec"]["strategy"]["type"] == "RollingUpdate"


@pytest.mark.parametrize("service", SERVICES)
def test_deployment_has_readiness_probe(service: str):
    doc = load_yaml(K8S_ROOT / service / "deployment.yaml")
    container = doc["spec"]["template"]["spec"]["containers"][0]
    assert "readinessProbe" in container
    assert container["readinessProbe"]["httpGet"]["path"] == "/health"


@pytest.mark.parametrize("service", SERVICES)
def test_deployment_has_liveness_probe(service: str):
    doc = load_yaml(K8S_ROOT / service / "deployment.yaml")
    container = doc["spec"]["template"]["spec"]["containers"][0]
    assert "livenessProbe" in container
    assert container["livenessProbe"]["httpGet"]["path"] == "/health"


@pytest.mark.parametrize("service", SERVICES)
def test_deployment_has_resource_limits(service: str):
    doc = load_yaml(K8S_ROOT / service / "deployment.yaml")
    container = doc["spec"]["template"]["spec"]["containers"][0]
    assert "resources" in container
    assert "limits" in container["resources"]
    assert "requests" in container["resources"]


@pytest.mark.parametrize("service", SERVICES)
def test_hpa_min_replicas_is_at_least_two(service: str):
    doc = load_yaml(K8S_ROOT / service / "hpa.yaml")
    assert doc["spec"]["minReplicas"] >= 2


@pytest.mark.parametrize("service", SERVICES)
def test_all_resources_in_asr_platform_namespace(service: str):
    for manifest in ["deployment.yaml", "service.yaml", "hpa.yaml"]:
        path = K8S_ROOT / service / manifest
        if path.exists():
            doc = load_yaml(path)
            assert doc["metadata"]["namespace"] == "asr-platform"


def test_namespace_manifest_exists():
    assert (K8S_ROOT / "namespace.yaml").exists()


def test_namespace_is_asr_platform():
    doc = load_yaml(K8S_ROOT / "namespace.yaml")
    assert doc["metadata"]["name"] == "asr-platform"


def test_api_gateway_uses_loadbalancer():
    doc = load_yaml(K8S_ROOT / "api-gateway" / "service.yaml")
    assert doc["spec"]["type"] == "LoadBalancer"


@pytest.mark.parametrize("service", [s for s in SERVICES if s != "api-gateway"])
def test_internal_services_use_clusterip(service: str):
    doc = load_yaml(K8S_ROOT / service / "service.yaml")
    assert doc["spec"]["type"] == "ClusterIP"
