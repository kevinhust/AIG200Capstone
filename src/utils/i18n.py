"""
Internationalization (i18n) module for Health Butler Discord Bot.

Support for multiple languages. Provides a clean API for users to get localized text
    based on their language preference stored in user profile.

Architecture:
    - User profile table with `preferences_json` column
    - Per-user language in `preferences_json` table (added via migration)
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import json

logger = logging.getLogger(__name__)


# Alias for backward compatibility
I18NConfig = None  # Will be replaced by I18N class


class I18N:
    """Internationalization manager for multi-language support."""

    def __init__(
        self,
        default_lang: str = "zh",
        fallback_lang: str = "en",
        translations_dir: Optional[Path] = None
    ):
        """
        Initialize the i18n manager.

        Args:
            default_lang: Default language code (default: "zh")
            fallback_lang: Fallback language code (default: "en")
            translations_dir: Directory containing translation JSON files
        """
        self.default_lang = default_lang
        self.fallback_lang = fallback_lang
        self.translations_dir = translations_dir
        self._load_on_startup = True
        self._current_lang: Optional[str] = None
        self._translations: Dict[str, Dict[str, Any]] = {}

        if translations_dir:
            self._load_translations()

    def _load_translations(self) -> None:
        """Load all translation files from the translations directory."""
        if not self.translations_dir:
            return

        if not self.translations_dir.exists():
            logger.warning(f"Translations directory not found: {self.translations_dir}")
            self._load_on_startup = False
            return

        # Load JSON files
        for file_path in self.translations_dir.glob("*.json"):
            self._load_translation_file(file_path)

        logger.info(f"Loaded translations from {self.translations_dir}")
        logger.info(f"i18n module initialized with {len(self._translations)} languages")

    def _load_translation_file(self, file_path: Path) -> None:
        """Load a single translation file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    logger.warning(f"Invalid translation file format: {file_path}")
                    return
                # Use file stem (e.g., "en", "zh") as language key
                lang_code = file_path.stem
                self._translations[lang_code] = data
                logger.debug(f"Loaded {len(data)} translations from {file_path}")
        except Exception as e:
            logger.error(f"Error loading translation file {file_path}: {e}")
            self._load_on_startup = False

    def get_text(self, key: str, lang: Optional[str] = None, **kwargs) -> str:
        """
        Get localized text by key.

        Args:
            key: Translation key (e.g., "onboarding.welcome_title")
            lang: Language code (e.g., "zh", "en"). If None, uses current/default language.
            **kwargs: Additional context variables for string formatting

        Returns:
            Localized text string, or the key itself if not found
        """
        if not self._load_on_startup:
            logger.warning("i18n module not properly initialized")
            return key

        if lang is None:
            lang = self._current_lang or self.default_lang

        if lang not in self._translations:
            logger.warning(f"Language '{lang}' not found in translations")
            return key

        # Support nested keys like "onboarding.welcome_title"
        text = self._get_nested_value(self._translations[lang], key)
        if text is None:
            logger.debug(f"Missing translation key: {key} in {lang}")
            return key

        # Format with kwargs
        if kwargs and isinstance(text, str):
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"Error formatting text: {e}")

        return text

    def _get_nested_value(self, data: dict, key: str) -> Optional[Any]:
        """Get a nested value from a dict using dot notation."""
        keys = key.split(".")
        value = data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        return value

    def set_language(self, lang: str) -> bool:
        """
        Set the current language for the session.

        Args:
            lang: Language code to set

        Returns:
            True if language was set, False if language not available
        """
        if lang not in self._translations:
            logger.warning(f"Language '{lang}' not found")
            return False
        self._current_lang = lang
        logger.info(f"Language set to {lang}")
        return True

    def get_current_language(self) -> str:
        """Get the current language for this session."""
        return self._current_lang or self.default_lang

    def get_available_languages(self) -> List[str]:
        """Get list of available languages."""
        return list(self._translations.keys()) if self._translations else [self.default_lang]

    def load_user_language_preference(self, user_id: str, db=None) -> str:
        """
        Load user's language preference from database.

        Args:
            user_id: Discord user ID
            db: Database connection (optional, will be fetched if not provided)

        Returns:
            Language code or default language if not found
        """
        try:
            if db is None:
                from src.discord_bot.profile_db import get_profile_db
                db = get_profile_db()
            profile = db.get_profile(user_id)
            if profile:
                prefs = profile.get("preferences_json", {}) or profile.get("preferences", {})
                if prefs and "language" in prefs:
                    return prefs["language"]
        except Exception as e:
            logger.warning(f"Error loading user language preference: {e}")
        return self.default_lang
