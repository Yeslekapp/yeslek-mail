from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


class I18nService:
    def __init__(
        self,
        *,
        directory: Path,
        default_locale: str,
        supported_locales: tuple[str, ...],
    ) -> None:
        self._directory = directory
        self._default_locale = default_locale
        self._supported_locales = supported_locales
        self._translations: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

        self.reload()

    def reload(self) -> None:
        loaded_translations: dict[str, dict[str, Any]] = {}

        for locale in self._supported_locales:
            file_path = self._directory / f"{locale}.json"

            if not file_path.exists():
                loaded_translations[locale] = {}
                continue

            with file_path.open(
                "r",
                encoding="utf-8",
            ) as translation_file:
                data = json.load(translation_file)

            if not isinstance(data, dict):
                raise RuntimeError(
                    f"Le fichier {file_path} doit contenir un objet JSON."
                )

            loaded_translations[locale] = data

        with self._lock:
            self._translations = loaded_translations

    def get(
        self,
        *,
        key: str,
        locale: str | None = None,
        **values: object,
    ) -> str:
        selected_locale = (
            locale
            if locale in self._supported_locales
            else self._default_locale
        )

        with self._lock:
            result = self._resolve(
                self._translations.get(
                    selected_locale,
                    {},
                ),
                key,
            )

            if result is None:
                result = self._resolve(
                    self._translations.get(
                        self._default_locale,
                        {},
                    ),
                    key,
                )

        if not isinstance(result, str):
            return key

        if not values:
            return result

        try:
            return result.format(**values)
        except (KeyError, ValueError):
            return result

    @staticmethod
    def _resolve(
        data: dict[str, Any],
        key: str,
    ) -> Any:
        value: Any = data

        for part in key.split("."):
            if not isinstance(value, dict):
                return None

            value = value.get(part)

            if value is None:
                return None

        return value