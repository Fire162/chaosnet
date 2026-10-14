"""Shared test doubles.

FakeToxiproxy answers exactly like the real Toxiproxy 2.12.0 (status codes and bodies
were recorded from the lab on 2026-10-14): 200 on create, 409 for an existing toxic
name, 404 for an unknown proxy or toxic, 204 on delete and reset.
"""

import json
from typing import Any

import httpx

API = "http://toxiproxy:8474"
LINK = "orders-inventory"


class FakeToxiproxy:
    def __init__(self) -> None:
        self.toxics: dict[str, list[dict[str, Any]]] = {"gateway-orders": [], LINK: []}
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        parts = request.url.path.strip("/").split("/")
        if request.method == "POST" and parts == ["reset"]:
            for toxics in self.toxics.values():
                toxics.clear()
            return httpx.Response(204)
        if request.method == "GET" and parts == ["proxies"]:
            return httpx.Response(
                200, json={k: {"name": k, "toxics": v} for k, v in self.toxics.items()}
            )
        if len(parts) >= 3 and parts[0] == "proxies" and parts[2] == "toxics":
            link = parts[1]
            if link not in self.toxics:
                return httpx.Response(404, json={"error": "proxy not found", "status": 404})
            toxics = self.toxics[link]
            if request.method == "POST" and len(parts) == 3:
                toxic = json.loads(request.content)
                if any(t["name"] == toxic["name"] for t in toxics):
                    return httpx.Response(
                        409, json={"error": "toxic already exists", "status": 409}
                    )
                toxic.setdefault("toxicity", 1)
                toxics.append(toxic)
                return httpx.Response(200, json=toxic)
            if request.method == "DELETE" and len(parts) == 4:
                if not any(t["name"] == parts[3] for t in toxics):
                    return httpx.Response(404, json={"error": "toxic not found", "status": 404})
                toxics[:] = [t for t in toxics if t["name"] != parts[3]]
                return httpx.Response(204)
        return httpx.Response(400, json={"error": "fake does not support this request"})

    def posted(self) -> list[dict[str, Any]]:
        return [json.loads(r.content) for r in self.requests if r.method == "POST" and r.content]
