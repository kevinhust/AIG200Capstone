"""
Unit tests for i18n (Internationalization) module.
"""

import pytest
from unittest.mock import Mock, patch
from src.utils.i18n import I18N


class TestI18NInitialization:
    """Test i18n module initialization."""

    def test_init_default_params(self):
        """i18n should initialize with default parameters."""
        i18n = I18N(
            default_lang="zh",
            fallback_lang="en"
        )
        assert i18n.default_lang == "zh"
        assert i18n.fallback_lang == "en"

    def test_init_missing_translations_dir(self, tmp_path):
        """Test graceful handling when translations directory doesn't exist."""
        i18n = I18N(translations_dir=tmp_path)
        assert i18n.translations_dir == tmp_path


class TestI18NGetText:
    """Test getting localized text."""

    @pytest.fixture
    def i18n_with_translations(self, tmp_path):
        """Create an i18n instance with loaded translations."""
        i18n = I18N(
            default_lang="zh",
            fallback_lang="en",
            translations_dir=tmp_path
        )
        # Manually set translations for testing
        i18n._translations = {
            "zh": {
                "onboarding": {
                    "welcome_title": "👋 欢迎来到健康管家！",
                    "welcome_description": "我是你的个人健康管家。",
                    "step_1_description": "请输入你的基础生理数据"
                },
                "buttons": {
                    "start_setup": "开始设置"
                }
            },
            "en": {
                "onboarding": {
                    "welcome_title": "👋 Welcome to Health Butler!",
                    "welcome_description": "I'm your personal health assistant.",
                    "step_1_description": "Please enter your basic metrics for TDEE calculation."
                },
                "buttons": {
                    "start_setup": "Start Setup"
                }
            }
        }
        i18n._load_on_startup = True
        return i18n

    def test_get_text_default_language(self, i18n_with_translations):
        """Test getting text in default language."""
        i18n = i18n_with_translations
        i18n._current_lang = "zh"
        assert i18n.get_text("onboarding.welcome_title") == "👋 欢迎来到健康管家！"

    def test_get_text_specific_language(self, i18n_with_translations):
        """Test getting text in a specific language."""
        i18n = i18n_with_translations
        assert i18n.get_text("onboarding.welcome_title", lang="en") == "👋 Welcome to Health Butler!"
        assert i18n.get_text("onboarding.step_1_description", lang="en") == "Please enter your basic metrics for TDEE calculation."

    def test_get_text_missing_key(self, i18n_with_translations):
        """Test that missing keys return the key itself."""
        i18n = i18n_with_translations
        assert i18n.get_text("nonexistent.key", lang="en") == "nonexistent.key"

    def test_get_text_with_formatting(self, i18n_with_translations):
        """Test text with placeholder formatting."""
        i18n = i18n_with_translations
        # Add a template with placeholder
        i18n._translations["zh"]["onboarding"]["greeting"] = "你好，{user_name}！"
        result = i18n.get_text("onboarding.greeting", lang="zh", user_name="Test User")
        assert result == "你好，Test User！"

    def test_get_available_languages(self, i18n_with_translations):
        """Test getting list of available languages."""
        i18n = i18n_with_translations
        assert set(i18n.get_available_languages()) == {"zh", "en"}


class TestI18NSetLanguage:
    """Test setting language."""

    @pytest.fixture
    def i18n_with_translations(self):
        """Create an i18n instance with loaded translations."""
        i18n = I18N(default_lang="zh", fallback_lang="en")
        i18n._translations = {"zh": {}, "en": {}}
        i18n._load_on_startup = True
        return i18n

    def test_set_language_valid(self, i18n_with_translations):
        """Test setting a valid language."""
        i18n = i18n_with_translations
        i18n.set_language("zh")
        assert i18n._current_lang == "zh"

    def test_set_language_invalid(self, i18n_with_translations):
        """Test that invalid language is rejected."""
        i18n = i18n_with_translations
        i18n._current_lang = "zh"
        i18n.set_language("fr")  # Should warn and not change
        assert i18n._current_lang == "zh"


class TestI18NUserPreference:
    """Test loading user language preference from database."""

    @pytest.fixture
    def i18n_with_mock_db(self):
        """Create an i18n instance with mock database."""
        i18n = I18N(default_lang="zh", fallback_lang="en")
        i18n._translations = {"zh": {}, "en": {}}
        i18n._load_on_startup = True
        return i18n

    def test_load_preference_success(self, i18n_with_mock_db):
        """Test successful loading of user preference."""
        i18n = i18n_with_mock_db
        mock_db = Mock()
        mock_profile = {
            "preferences_json": {"language": "en"}
        }
        mock_db.get_profile.return_value = mock_profile

        result = i18n.load_user_language_preference("123456789", mock_db)
        assert result == "en"

    def test_load_preference_not_found(self, i18n_with_mock_db):
        """Test handling when user preference not found in database."""
        i18n = i18n_with_mock_db
        mock_db = Mock()
        mock_db.get_profile.return_value = {}

        result = i18n.load_user_language_preference("123456789", mock_db)
        assert result == "zh"  # Fallback to default

    def test_load_preference_no_language_key(self, i18n_with_mock_db):
        """Test handling when preferences exist but no language key."""
        i18n = i18n_with_mock_db
        mock_db = Mock()
        mock_db.get_profile.return_value = {"preferences_json": {"theme": "dark"}}

        result = i18n.load_user_language_preference("123456789", mock_db)
        assert result == "zh"  # Fallback to default


class TestI18NIntegration:
    """Test i18n integration scenarios."""

    @pytest.fixture
    def i18n_full(self):
        """Create a fully configured i18n instance."""
        i18n = I18N(default_lang="zh", fallback_lang="en")
        i18n._translations = {
            "zh": {
                "onboarding": {
                    "welcome_title": "👋 欢迎来到健康管家！",
                    "step_1_description": "请输入你的基础生理数据",
                    "step_2_description": "选择你的性别和健身目标",
                    "step_3_description": "帮助我们了解你的过敏源",
                    "privacy_title": "🔒 隐私优先",
                    "privacy_description": "• 设置在 **#general** 公共频道完成\n• 设置完成后，我会创建一个 **私人频道**"
                },
                "buttons": {
                    "start_setup": "开始设置",
                    "view_terms": "查看条款",
                    "learn_more": "了解更多"
                }
            },
            "en": {
                "onboarding": {
                    "welcome_title": "👋 Welcome to Health Butler!",
                    "step_1_description": "Please enter your basic metrics for TDEE calculation.",
                    "step_2_description": "Select your biological sex, fitness goal, and activity level.",
                    "step_3_description": "Help us understand any allergies and health conditions.",
                    "privacy_title": "🔒 Privacy First",
                    "privacy_description": "• Setup happens in **#general** (public channel)\n• After setup, I'll create a **private channel** just for you!"
                },
                "buttons": {
                    "start_setup": "Start Setup",
                    "view_terms": "View Terms",
                    "learn_more": "Learn More"
                }
            }
        }
        i18n._load_on_startup = True
        return i18n

    def test_full_onboarding_flow_zh(self, i18n_full):
        """Test full onboarding flow in Chinese."""
        i18n = i18n_full
        i18n.set_language("zh")

        # Verify all onboarding keys are available
        assert i18n.get_text("onboarding.welcome_title") == "👋 欢迎来到健康管家！"
        assert i18n.get_text("onboarding.step_1_description") == "请输入你的基础生理数据"
        assert i18n.get_text("buttons.start_setup") == "开始设置"

    def test_full_onboarding_flow_en(self, i18n_full):
        """Test full onboarding flow in English."""
        i18n = i18n_full
        i18n.set_language("en")

        # Verify all onboarding keys are available
        assert i18n.get_text("onboarding.welcome_title") == "👋 Welcome to Health Butler!"
        assert i18n.get_text("onboarding.step_1_description") == "Please enter your basic metrics for TDEE calculation."
        assert i18n.get_text("buttons.start_setup") == "Start Setup"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
