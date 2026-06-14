# © 2026 Manoj Mallick. LLMWatch.
"""Install every Dashboard Studio JSON in dashboards/ into Splunk via REST.

Each dashboards/<name>.json (a Dashboard Studio definition) becomes a view
named <name> in the `search` app, shared at app level. Idempotent: existing
views are deleted and recreated.

Requires: SPLUNK_USER, SPLUNK_PASSWORD (defaults localhost:8089).
"""

from __future__ import annotations

import glob
import json
import os
import sys
import urllib3
from xml.sax.saxutils import escape

import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REST = os.environ.get("SPLUNK_REST_URL", "https://localhost:8089")
USER = os.environ.get("SPLUNK_USER", "admin")
PW = os.environ.get("SPLUNK_PASSWORD", "")
APP = "search"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def view_xml(definition: str, label: str) -> str:
    # label sits outside CDATA → must be XML-escaped (& < > in titles break it)
    return (f'<dashboard version="2" theme="dark">\n  <label>{escape(label)}</label>\n'
            f'  <definition><![CDATA[\n{definition}\n]]></definition>\n'
            f'  <meta type="hiddenElements"><hiddenElement>splunk.header</hiddenElement>'
            f'<hiddenElement>splunk.footer</hiddenElement></meta>\n</dashboard>')


def install(path: str) -> str:
    name = os.path.splitext(os.path.basename(path))[0]
    defn = open(path).read()
    label = json.loads(defn)["title"]                     # also validates JSON
    auth = (USER, PW)
    base = f"{REST}/servicesNS/{USER}/{APP}/data/ui/views"
    for owner in ("nobody", USER):
        requests.delete(f"{REST}/servicesNS/{owner}/{APP}/data/ui/views/{name}",
                        auth=auth, verify=False, params={"output_mode": "json"}, timeout=30)
    r = requests.post(base, auth=auth, verify=False,
                      data={"name": name, "eai:data": view_xml(defn, label),
                            "output_mode": "json"}, timeout=30)
    r.raise_for_status()
    requests.post(f"{base}/{name}/acl", auth=auth, verify=False,
                  data={"owner": USER, "sharing": "app", "perms.read": "*",
                        "output_mode": "json"}, timeout=30)
    return name


def main() -> None:
    if not PW:
        sys.exit("export SPLUNK_PASSWORD first")
    files = sorted(glob.glob(os.path.join(HERE, "dashboards", "*.json")))
    if not files:
        sys.exit("no dashboards/*.json found")
    for path in files:
        try:
            name = install(path)
            print(f"  [+] {name}  →  http://localhost:8989/en-US/app/{APP}/{name}")
        except (requests.HTTPError, json.JSONDecodeError, KeyError) as e:
            print(f"  [!] {os.path.basename(path)} failed: {e}")


if __name__ == "__main__":
    main()
