import discord
from discord import ui
import logging

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

            # Trigger callback (usually defined in bot.py to handle state/View transition)
            await self.on_submit_callback(interaction, data)

        except ValueError:
            await interaction.response.send_message("⚠️ Please enter valid numeric values.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in RegistrationModal: {e}")
            await interaction.response.send_message("⚠️ An unexpected error occurred.", ephemeral=True)
