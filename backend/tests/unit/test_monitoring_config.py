import importlib
import json
import re
from pathlib import Path
from typing import Any

import yaml
from prometheus_client import REGISTRY

ROOT = Path(__file__).resolve().parents[3]
MONITORING = ROOT / "monitoring"
DASHBOARD = MONITORING / "grafana" / "dashboards" / "alpha-impact.json"
DATASOURCES = MONITORING / "grafana" / "provisioning" / "datasources" / "datasources.yml"
APP_METRIC = re.compile(r"\b(?:http|llm)_[a-z_]+")
SAMPLE_SUFFIXES = ("_total", "_bucket", "_count", "_sum")


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def panels() -> list[Any]:
    panels: list[Any] = json.loads(DASHBOARD.read_text(encoding="utf-8"))["panels"]
    return panels


def queries(datasource: str) -> list[str]:
    return [
        target["expr"]
        for panel in panels()
        if panel["datasource"]["uid"] == datasource
        for target in panel["targets"]
    ]


def exported_samples() -> set[str]:
    importlib.import_module("main")
    return {family.name + suffix for family in REGISTRY.collect() for suffix in SAMPLE_SUFFIXES}


def test_prometheus_scrapes_the_api_on_its_compose_metrics_port() -> None:
    port = load_yaml(ROOT / "docker-compose.yml")["services"]["api"]["environment"]["METRICS_PORT"]
    job = load_yaml(MONITORING / "prometheus" / "prometheus.yml")["scrape_configs"][0]
    assert job["static_configs"] == [{"targets": [f"api:{port}"]}]


def test_dashboard_reads_only_provisioned_datasources() -> None:
    provisioned = {source["uid"] for source in load_yaml(DATASOURCES)["datasources"]}
    assert {panel["datasource"]["uid"] for panel in panels()} == provisioned


def test_dashboard_queries_only_metrics_the_app_exports(settings_env: dict[str, str]) -> None:
    used = {name for expr in queries("prometheus") for name in APP_METRIC.findall(expr)}
    assert used
    assert used <= exported_samples()


def test_dashboard_shows_api_logs() -> None:
    assert any('service="api"' in expr for expr in queries("loki"))
