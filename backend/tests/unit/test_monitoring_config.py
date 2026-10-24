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
SAMPLE_SUFFIXES = ("", "_total", "_bucket", "_count", "_sum")


def env_example() -> dict[str, str]:
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    pairs = (line.split("=", 1) for line in lines if line and not line.startswith("#"))
    return {name: value for name, value in pairs}


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def targets() -> list[Any]:
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    return [target for panel in dashboard["panels"] for target in panel.get("targets", [])]


def queries(datasource: str) -> list[str]:
    return [target["expr"] for target in targets() if target["datasource"]["uid"] == datasource]


def exported_samples() -> set[str]:
    importlib.import_module("main")
    importlib.import_module("apps.services.llm.metrics")
    return {family.name + suffix for family in REGISTRY.collect() for suffix in SAMPLE_SUFFIXES}


def test_prometheus_scrapes_the_api_on_the_metrics_port() -> None:
    config = load_yaml(MONITORING / "prometheus" / "prometheus.yml")
    scraped = [
        target
        for job in config["scrape_configs"]
        for static in job["static_configs"]
        for target in static["targets"]
    ]
    assert scraped == [f"api:{env_example()['METRICS_PORT']}"]


def test_dashboard_reads_only_provisioned_datasources() -> None:
    provisioned = {source["uid"] for source in load_yaml(DATASOURCES)["datasources"]}
    assert {target["datasource"]["uid"] for target in targets()} == provisioned


def test_dashboard_queries_only_metrics_the_app_exports(settings_env: dict[str, str]) -> None:
    used = {name for expr in queries("prometheus") for name in APP_METRIC.findall(expr)}
    assert used
    assert used <= exported_samples()


def test_dashboard_shows_api_logs() -> None:
    assert any('service="api"' in expr for expr in queries("loki"))
