from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .models import WorkRecord


class NotionError(RuntimeError):
    pass


class NotionReadOnlyClient:
    """Read-only adapter for the Notion Data Sources API."""

    def __init__(
        self,
        token: str | None = None,
        data_source_id: str | None = None,
        notion_version: str | None = None,
    ) -> None:
        self.token = token or os.getenv("NOTION_TOKEN", "")
        self.data_source_id = data_source_id or os.getenv("NOTION_DATA_SOURCE_ID", "")
        self.notion_version = notion_version or os.getenv("NOTION_VERSION", "2026-03-11")
        if not self.token:
            raise NotionError("NOTION_TOKEN تنظیم نشده است.")
        if not self.data_source_id:
            raise NotionError("NOTION_DATA_SOURCE_ID تنظیم نشده است.")

    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": self.notion_version,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise NotionError(f"Notion API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise NotionError(f"خطای اتصال به Notion: {exc}") from exc

    @staticmethod
    def _plain_text(items: list[dict[str, Any]]) -> str:
        return "".join(str(item.get("plain_text", "")) for item in items).strip()

    @classmethod
    def _value(cls, prop: dict[str, Any]) -> Any:
        kind = prop.get("type")
        if kind in {"title", "rich_text"}:
            return cls._plain_text(prop.get(kind, []))
        if kind in {"select", "status"}:
            item = prop.get(kind)
            return item.get("name", "") if item else ""
        if kind == "people":
            return [
                p.get("name") or p.get("id", "")
                for p in prop.get("people", [])
            ]
        if kind == "url":
            return prop.get("url") or ""
        if kind == "date":
            value = prop.get("date")
            return value.get("start", "") if value else ""
        if kind == "checkbox":
            return bool(prop.get("checkbox"))
        if kind == "number":
            return prop.get("number")
        if kind == "relation":
            return [x.get("id", "") for x in prop.get("relation", [])]
        return ""

    @classmethod
    def _record_from_page(cls, page: dict[str, Any]) -> WorkRecord:
        properties = page.get("properties", {})
        flat = {name: cls._value(value) for name, value in properties.items()}
        flat["url"] = page.get("url", "")
        return WorkRecord.from_dict(flat)

    def query_all(self) -> list[WorkRecord]:
        url = f"https://api.notion.com/v1/data_sources/{self.data_source_id}/query"
        records: list[WorkRecord] = []
        cursor: str | None = None

        while True:
            payload: dict[str, Any] = {"page_size": 100}
            if cursor:
                payload["start_cursor"] = cursor
            data = self._post(url, payload)
            records.extend(self._record_from_page(page) for page in data.get("results", []))
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                raise NotionError("Notion has_more=true ولی next_cursor خالی است.")
        return records
