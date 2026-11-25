"""XML, YAML, TOML and XLSX summaries: smaller than the file, never shrinking with the level."""
import json

import pytest

from token_shredder.main import convert_file
from token_shredder.metrics import TokenCounter

count = TokenCounter().estimate


def _levels(path, tmp_path):
    return [convert_file(str(path), detail_level=lv, show_metrics=False, cache_enabled=False,
                         write_output=False).markdown for lv in range(1, 6)]


def _assert_shape(outs, raw):
    sizes = [count(o) for o in outs]
    assert sizes == sorted(sizes), sizes
    assert all(s <= count(raw) + 8 for s in sizes[:4]), (sizes, count(raw))


RSS = ('<?xml version="1.0"?><rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>'
       '<title>News</title><link>https://news.example.com</link>'
       + "".join(f'<item><title>Story number {i} about things</title><link>https://news.example.com/{i}</link>'
                 f'<pubDate>Mon, {i % 28 + 1:02d} Jan 2024 10:00:00 GMT</pubDate>'
                 f'<description>{"Long description text. " * 20}{i}</description><dc:creator>Ann</dc:creator></item>'
                 for i in range(25))
       + '</channel></rss>')

POM = ('<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion>'
       '<groupId>com.acme</groupId><artifactId>app</artifactId><version>1.0</version><dependencies>'
       + "".join(f'<dependency><groupId>org.lib{i}</groupId><artifactId>lib-{i}</artifactId>'
                 f'<version>{i}.1</version><scope>test</scope></dependency>' for i in range(12))
       + '</dependencies></project>')


def test_xml_rss_levels(tmp_path):
    f = tmp_path / "feed.xml"
    f.write_text(RSS)
    outs = _levels(f, tmp_path)
    _assert_shape(outs, RSS)
    assert "item ×25" in outs[0] and "Story number" not in outs[0]
    assert "@" not in outs[0] and "pubDate" in outs[0]
    assert "Repeated `rss/channel/item`" in outs[1]
    l3 = outs[2]
    assert "Story number 3 about things | https://news.example.com/3" in l3
    assert "Long description text. Long" not in l3          # long prose is left out of item lines
    assert count(l3) < count(RSS) / 3


def test_xml_pom_dependencies_one_line_each(tmp_path):
    f = tmp_path / "pom.xml"
    f.write_text(POM)
    outs = _levels(f, tmp_path)
    _assert_shape(outs, POM)
    assert "org.lib3:lib-3:3.1" in outs[2]
    assert "all scope=test" in outs[2]
    assert "<dependency>" not in outs[2]


def test_xml_namespaces_and_attributes(tmp_path):
    xml = ('<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.x">'
           + "".join(f'<uses-permission android:name="perm.P{i}"/>' for i in range(12)) + '</manifest>')
    f = tmp_path / "AndroidManifest.xml"
    f.write_text(xml)
    outs = _levels(f, tmp_path)
    _assert_shape(outs, xml)
    assert "android:name" in outs[1] and "perm.P2" in outs[2]


def test_xml_tiny_and_invalid_files(tmp_path):
    f = tmp_path / "t.xml"
    f.write_text("<a><b>1</b></a>")
    outs = _levels(f, tmp_path)
    assert all("<a><b>1</b></a>" in o for o in outs)
    f.write_text("<a><b>")
    assert "<a><b>" in _levels(f, tmp_path)[2]            # unparseable: the text itself, no error


K8S = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  labels:
    app: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    spec:
      containers:
        - name: web
          image: nginx:1.25
          args: ["--port", "8080", "--verbose", "--log-level", "debug", "--config", "/etc/web/config.yaml"]
          env:
            - {name: MODE, value: production}
            - {name: LOG, value: info}
            - {name: REGION, value: eu-west-1}
---
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-config
data:
  config.yaml: |
    port: 8080
    verbose: true
    log_level: debug
    upstreams:
      - http://a.internal
      - http://b.internal
"""


def test_yaml_multi_document(tmp_path):
    f = tmp_path / "k8s.yaml"
    f.write_text(K8S * 1)
    outs = _levels(f, tmp_path)
    _assert_shape(outs, K8S)
    assert "3 documents" in outs[0]
    for kind in ("Deployment `web`", "Service `web-svc`", "ConfigMap `web-config`"):
        assert kind in outs[0]
    assert "replicas" not in outs[0] and "replicas" in outs[1]
    assert "---" in outs[3] and "nginx:1.25" in outs[3]
    assert count(outs[2]) <= count(K8S) + 8


def test_yaml_levels_on_a_larger_file(tmp_path):
    steps = "".join(f"      - name: Step {i}\n        run: |\n          echo {i}\n          make test-{i}\n" for i in range(12))
    text = ("# CI\nname: CI\non: [push, pull_request]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    strategy:\n      matrix:\n        python: [\"3.10\", \"3.11\", \"3.12\"]\n    steps:\n" + steps)
    f = tmp_path / "ci.yml"
    f.write_text(text)
    outs = _levels(f, tmp_path)
    _assert_shape(outs, text)
    assert "on: [push, pull_request]" in outs[2].replace('"on"', "on")      # `on` is not the boolean true
    assert "True" not in outs[2]
    assert "make test-5" in outs[3]
    assert count(outs[2]) < count(text)


def test_yaml_unknown_tags_and_syntax_errors(tmp_path):
    f = tmp_path / "cf.yaml"
    f.write_text("Resources:\n  Bucket:\n    Properties:\n      Name: !Ref Param\n      Tags: !GetAtt [A, B]\n")
    assert "Param" in _levels(f, tmp_path)[2]
    f.write_text("a: [1, 2\nb: : :\n")
    assert "b: : :" in _levels(f, tmp_path)[2]


def test_yaml_long_list_of_mappings_is_profiled(tmp_path):
    text = "users:\n" + "".join(f"  - id: {i}\n    name: user{i}\n    role: {'admin' if i % 5 == 0 else 'dev'}\n"
                               for i in range(60))
    f = tmp_path / "u.yaml"
    f.write_text(text)
    outs = _levels(f, tmp_path)
    _assert_shape(outs, text)
    assert "60 items" in outs[2] and "enum" in outs[2]
    assert "user59" in outs[3]


def test_toml_smaller_than_file_and_monotonic(tmp_path):
    text = ('[package]\nname = "demo"\nversion = "0.1.0"\n' + "".join(f'[dependencies.dep{i}]\nversion = "{i}.0"\n'
            f'features = ["a", "b", "c"]\noptional = true\n' for i in range(15)))
    f = tmp_path / "Cargo.toml"
    f.write_text(text)
    outs = _levels(f, tmp_path)
    _assert_shape(outs, text)
    assert "dependencies.dep3" in outs[0]


def test_xlsx_sizes_are_monotonic_on_tiny_sheets(tmp_path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["flag", "n"])
    for i in range(4):
        ws.append([i % 2 == 0, i])
    f = tmp_path / "tiny.xlsx"
    wb.save(f)
    sizes = [count(o) for o in _levels(f, tmp_path)]
    assert sizes == sorted(sizes), sizes


def test_json_constant_and_examples_in_converter(tmp_path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps([{"kind": "repo", "url": f"https://api.example.com/r/{i}", "id": i} for i in range(30)]))
    l3 = _levels(f, tmp_path)[2]
    assert "`kind`: string = repo" in l3
    assert l3.count("https://api.example.com") == 1
