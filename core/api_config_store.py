from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


class ApiConfigStore:
    def __init__(self, data_dir: Path | str):
        self.data_dir = Path(data_dir)
        self.current_path = self.data_dir / "api_config.json"
        self.history_path = self.data_dir / "api_config_history.json"

    @staticmethod
    def _clean(payload: dict[str, Any]) -> dict[str, Any]:
        data = {key: str(payload.get(key) or "").strip() for key in ("api_key", "provider", "model", "base_url")}
        data["provider"] = data["provider"] or "openai"
        return data

    @staticmethod
    def _config_id(data: dict[str, Any]) -> str:
        compact = "|".join(str(data.get(key) or "") for key in ("provider", "model", "base_url", "api_key"))
        return hashlib.sha1(compact.encode("utf-8", errors="ignore")).hexdigest()[:16]

    @staticmethod
    def _masked(data: dict[str, Any]) -> dict[str, Any]:
        if not data:
            return {}
        key = str(data.get("api_key") or "")
        return {
            "provider": data.get("provider", ""),
            "model": data.get("model", ""),
            "base_url": data.get("base_url", ""),
            "updated_at": data.get("updated_at", ""),
            "config_id": data.get("config_id", ""),
            "api_key_masked": key[:4] + "..." + key[-4:] if len(key) > 8 else ("已保存" if key else ""),
        }

    @staticmethod
    def _read(path: Path, default: Any) -> Any:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value
        except Exception:
            return default

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            try:
                shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
            except Exception:
                pass
        temp = path.with_suffix(path.suffix + f".{uuid.uuid4().hex}.tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except Exception:
                pass
        temp.replace(path)

    def _current(self) -> dict[str, Any]:
        value = self._read(self.current_path, {})
        return value if isinstance(value, dict) and value.get("api_key") else {}

    def _history(self) -> list[dict[str, Any]]:
        value = self._read(self.history_path, [])
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in value if isinstance(value, list) else []:
            if not isinstance(item, dict) or not item.get("api_key") or item.get("test_ok") is not True:
                continue
            row = dict(item)
            row["config_id"] = str(row.get("config_id") or self._config_id(row))
            if row["config_id"] in seen:
                continue
            seen.add(row["config_id"])
            rows.append(row)
        return rows[:12]

    def save_verified(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._clean(payload)
        if not data["api_key"] or not data["model"]:
            raise ValueError("API Key 和模型不能为空。")
        data.update({
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "config_id": self._config_id(data),
            "test_ok": True,
        })
        self._write(self.current_path, data)
        history = [data] + [row for row in self._history() if row.get("config_id") != data["config_id"]]
        self._write(self.history_path, history[:12])
        return data

    def current_masked(self) -> dict[str, Any]:
        return self._masked(self._current())

    def history_masked(self) -> list[dict[str, Any]]:
        current = self._current()
        rows = ([current] if current else []) + self._history()
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            config_id = str(row.get("config_id") or self._config_id(row))
            if config_id in seen:
                continue
            seen.add(config_id)
            row = {**row, "config_id": config_id}
            unique.append(self._masked(row))
        return unique[:12]

    def activate(self, config_id: str) -> dict[str, Any]:
        match = next((row for row in self._history() if str(row.get("config_id")) == str(config_id)), None)
        if not match:
            current = self._current()
            if str(current.get("config_id")) == str(config_id):
                match = current
        if not match:
            raise KeyError("未找到该历史 API 配置。")
        active = {**match, "updated_at": datetime.now().isoformat(timespec="seconds"), "test_ok": True}
        self._write(self.current_path, active)
        return self._masked(active)

    def resolve_request_config(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        request_data = self._clean(payload or {})
        if request_data["api_key"]:
            return request_data
        config_id = str((payload or {}).get("config_id") or "").strip()
        if config_id:
            self.activate(config_id)
        saved = self._current()
        if saved and ((payload or {}).get("use_saved_config") or config_id or not request_data["api_key"]):
            return {key: str(saved.get(key) or "").strip() for key in ("api_key", "provider", "model", "base_url")}
        return request_data

    def clear_all(self) -> None:
        for path in (self.current_path, self.history_path):
            try:
                path.unlink(missing_ok=True)
                path.with_suffix(path.suffix + ".bak").unlink(missing_ok=True)
            except Exception:
                pass
