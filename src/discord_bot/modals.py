import discord
from discord import ui
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RegistrationModal(ui.Modal, title='Step 1/3: Basic Metrics 🟢⚪⚪'):
    """
    Refactored Step 1 of onboarding.
    Focuses on Age, Height, and Weight for minimal mobile friction.
    """
    age = ui.TextInput(
        label='Age (13-100)',
        placeholder='e.g. 25',
        min_length=1,
        max_length=3,
        required=True
    )
    height = ui.TextInput(
        label='Height (cm)',
        placeholder='e.g. 175',
        min_length=2,
        max_length=3,
        required=True
    )
    weight = ui.TextInput(
        label='Weight (kg)',
        placeholder='e.g. 70',
        min_length=2,
        max_length=3,
        required=True
    )

    def __init__(self, on_submit_callback):
        super().__init__()
        self.on_submit_callback = on_submit_callback

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Basic validation
            age_val = int(str(self.age.value).strip())
            height_val = float(str(self.height.value).strip())
            weight_val = float(str(self.weight.value).strip())

            if not (13 <= age_val <= 100):
                return await interaction.response.send_message("⚠️ Age must be between 13 and 100.", ephemeral=True)
            if not (120 <= height_val <= 230):
                return await interaction.response.send_message("⚠️ Height must be between 120 and 230 cm.", ephemeral=True)
            if not (30 <= weight_val <= 300):
                return await interaction.response.send_message("⚠️ Weight must be between 30 and 300 kg.", ephemeral=True)

            # Collect data
            data = {
                "name": interaction.user.display_name,
                "age": age_val,
                "height_cm": height_val,
                "weight_kg": weight_val
            }

            # Trigger callback (usually defined in bot.py to handle state/View)
            await self.on_submit_callback(interaction, data)

        except ValueError:
            await interaction.response.send_message("⚠️ Please enter valid numeric values.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in RegistrationModal: {e}")
            await interaction.response.send_message("⚠️ An unexpected error occurred.", ephemeral=True)


class BYOKModal(ui.Modal, title="Configure Custom AI (BYOK)"):
    """Securely collect a user's LLM API credentials.

    Fields are sent ephemerally and persisted via ProfileDB.save_llm_config
    (pgcrypto-encrypted at rest). The plaintext key never appears in chat.
    """

    provider = ui.TextInput(
        label="Provider",
        placeholder="openai | anthropic | google | local | custom",
        default="openai",
        min_length=2,
        max_length=20,
        required=True,
    )
    base_url = ui.TextInput(
        label="Base URL (optional, for local LLMs)",
        placeholder="e.g. http://localhost:11434/v1",
        required=False,
        max_length=200,
    )
    api_key = ui.TextInput(
        label="API Key",
        placeholder="sk-... or leave blank for keyless local models",
        required=False,
        max_length=200,
    )
    model_name = ui.TextInput(
        label="Model Name (optional)",
        placeholder="e.g. gpt-4o, llama-3, gemini-2.5-flash",
        required=False,
        max_length=80,
    )

    def __init__(self, owner_type: str = "user") -> None:
        super().__init__()
        self._owner_type = owner_type

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Persist encrypted credentials and respond ephemerally."""
        from src.discord_bot import profile_utils as pu

        user_id = str(interaction.user.id)
        provider_val = (self.provider.value or "openai").strip().lower()
        base_url_val = (self.base_url.value or "").strip()
        api_key_val = (self.api_key.value or "").strip()
        model_val = (self.model_name.value or "").strip()

        if not api_key_val and not base_url_val:
            await interaction.response.send_message(
                "⚠️ You must provide at least an API key *or* a base URL for a local model.",
                ephemeral=True,
            )
            return

        if not pu.profile_db:
            await interaction.response.send_message(
                "⚠️ Database is not connected. Cannot save credentials right now.",
                ephemeral=True,
            )
            return

        try:
            pu.profile_db.save_llm_config(
                owner_id=user_id,
                owner_type=self._owner_type,
                provider=provider_val,
                api_key=api_key_val,
                base_url=base_url_val,
                model_name=model_val,
            )
            display_key = f"`{api_key_val[:4]}...{api_key_val[-4:]}`" if len(api_key_val) > 8 else "`(set)`"
            await interaction.response.send_message(
                f"✅ **BYOK credentials saved** (encrypted at rest).\n"
                f"• Provider: `{provider_val}`\n"
                f"• Base URL: `{base_url_val or '(default)'}`\n"
                f"• API Key: {display_key}\n"
                f"• Model: `{model_val or '(provider default)'}`\n\n"
                "Your next AI request will use these credentials.",
                ephemeral=True,
            )
        except Exception as exc:
            logger.error("BYOKModal save_llm_config failed for %s: %s", user_id, exc)
            await interaction.response.send_message(
                f"❌ Failed to save credentials: {exc}",
                ephemeral=True,
            )
