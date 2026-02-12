from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from health_butler.data.user_profiles import UserProfile
from health_butler.discord_bot.config import DiscordBotConfig
from health_butler.discord_bot.profiles import load_profile, save_profile
from health_butler.discord_bot.router import build_delegations, run_delegations


logger = logging.getLogger(__name__)


def _is_image_attachment(att: discord.Attachment) -> bool:
    if att.content_type and att.content_type.startswith("image/"):
        return True
    name = (att.filename or "").lower()
    return name.endswith((".png", ".jpg", ".jpeg", ".webp"))


def _chunk_message(text: str, limit: int = 1900) -> list[str]:
    """
    Discord has a 2000-char message limit. Keep some buffer for formatting.
    """
    text = text or ""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        chunks.append(text[start:end])
        start = end
    return chunks


class HealthButlerDiscordBot(commands.Bot):
    def __init__(self, cfg: DiscordBotConfig):
        intents = discord.Intents.default()
        intents.message_content = True  # required for on_message routing
        super().__init__(command_prefix="!", intents=intents)

        self.cfg = cfg
        self.tree = app_commands.CommandTree(self)

        # Lazy init heavy agents (ViT load can be slow)
        self._coordinator = None
        self._nutrition_agent = None
        self._fitness_agent = None

        # Ensure profile directory exists
        self.cfg.profile_dir.mkdir(parents=True, exist_ok=True)

    def _get_agents(self):
        # Local imports keep startup light
        from health_butler.coordinator.coordinator_agent import CoordinatorAgent
        from health_butler.agents.nutrition.nutrition_agent import NutritionAgent
        from health_butler.agents.fitness.fitness_agent import FitnessAgent

        if self._coordinator is None:
            self._coordinator = CoordinatorAgent()
        if self._nutrition_agent is None:
            self._nutrition_agent = NutritionAgent()
        if self._fitness_agent is None:
            self._fitness_agent = FitnessAgent()
        return self._coordinator, self._nutrition_agent, self._fitness_agent

    async def setup_hook(self) -> None:
        # Register slash commands

        @self.tree.command(name="ping", description="Check if the bot is alive.")
        async def ping(interaction: discord.Interaction):
            await interaction.response.send_message("pong", ephemeral=True)

        @self.tree.command(
            name="onboard",
            description="Create/update your profile (required for fitness advice).",
        )
        @app_commands.describe(
            age="Age in years",
            weight_kg="Weight in kilograms",
            height_cm="Height in centimeters (optional)",
            fitness_level="beginner/intermediate/advanced",
            limitations="Comma-separated (e.g. knee_injury, back_injury)",
            equipment="Comma-separated (e.g. home,gym,outdoor,none)",
        )
        async def onboard(
            interaction: discord.Interaction,
            age: int,
            weight_kg: float,
            height_cm: Optional[float] = None,
            fitness_level: str = "beginner",
            limitations: str = "",
            equipment: str = "home",
        ):
            # Gate by allowlists
            if not self.cfg.is_user_allowed(interaction.user.id):
                await interaction.response.send_message(
                    "You are not allowlisted for this demo.", ephemeral=True
                )
                return

            if interaction.channel_id is not None and not self.cfg.is_channel_allowed(
                interaction.channel_id
            ):
                await interaction.response.send_message(
                    "This channel is not allowlisted for this demo.", ephemeral=True
                )
                return

            lims = [x.strip() for x in (limitations or "").split(",") if x.strip()]
            eq = [x.strip() for x in (equipment or "").split(",") if x.strip()]
            if not eq:
                eq = ["none"]

            try:
                profile = UserProfile(
                    user_id=str(interaction.user.id),
                    age=age,
                    weight_kg=weight_kg,
                    height_cm=height_cm,
                    fitness_level=fitness_level if fitness_level in ("beginner", "intermediate", "advanced") else "beginner",
                    health_limitations=lims,
                    available_equipment=eq,
                )
                save_profile(self.cfg.profile_dir, profile, interaction.user.id)
            except Exception as exc:
                await interaction.response.send_message(
                    f"Failed to save profile: {exc}", ephemeral=True
                )
                return

            await interaction.response.send_message(
                f"✅ Onboarded. Profile saved for user `{interaction.user.id}`.",
                ephemeral=True,
            )

        @self.tree.command(
            name="profile",
            description="Show your saved onboarding profile (ephemeral).",
        )
        async def profile(interaction: discord.Interaction):
            if not self.cfg.is_user_allowed(interaction.user.id):
                await interaction.response.send_message(
                    "You are not allowlisted for this demo.", ephemeral=True
                )
                return

            try:
                p = load_profile(self.cfg.profile_dir, interaction.user.id)
            except Exception as exc:
                await interaction.response.send_message(
                    f"No profile found. Run `/onboard` first.\n({exc})",
                    ephemeral=True,
                )
                return

            bmi = p.bmi
            await interaction.response.send_message(
                f"**Profile**\n"
                f"- age: {p.age}\n"
                f"- weight_kg: {p.weight_kg}\n"
                f"- height_cm: {p.height_cm}\n"
                f"- fitness_level: {p.fitness_level}\n"
                f"- limitations: {', '.join(p.health_limitations) if p.health_limitations else 'none'}\n"
                f"- equipment: {', '.join(p.available_equipment) if p.available_equipment else 'none'}\n"
                f"- bmi: {bmi if bmi is not None else 'n/a'}\n",
                ephemeral=True,
            )

        # Sync commands
        if self.cfg.guild_id:
            guild = discord.Object(id=self.cfg.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("Synced commands to guild %s", self.cfg.guild_id)
        else:
            await self.tree.sync()
            logger.info("Synced global commands")

    async def on_ready(self):
        logger.info("Logged in as %s (id=%s)", self.user, self.user.id if self.user else "?")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Gate by allowlists
        if not self.cfg.is_user_allowed(message.author.id):
            return

        if message.channel and not self.cfg.is_channel_allowed(message.channel.id):
            return

        # Avoid reacting to slash command invocations, etc.
        content = (message.content or "").strip()
        if not content and not message.attachments:
            return

        # If user isn't onboarded, we still allow nutrition (image/meal) but we block fitness personalization.
        user_profile: Optional[UserProfile] = None
        try:
            user_profile = load_profile(self.cfg.profile_dir, message.author.id)
        except Exception:
            user_profile = None

        image_path: Optional[Path] = None
        try:
            img_atts = [a for a in message.attachments if _is_image_attachment(a)]
            if img_atts:
                att = img_atts[0]
                suffix = Path(att.filename).suffix or ".jpg"
                tmp = Path("/tmp") / f"discord_upload_{message.id}{suffix}"
                await att.save(tmp)
                image_path = tmp
        except Exception as exc:
            await message.reply(f"Failed to process image attachment: {exc}")
            return

        coordinator, nutrition_agent, fitness_agent = self._get_agents()

        delegations = build_delegations(
            coordinator,
            content if content else "Analyze this meal.",
            has_image=image_path is not None,
        )

        # Execute in a thread to avoid blocking event loop (Gemini/Vision/RAG are sync)
        def _run_sync():
            return run_delegations(
                nutrition_agent=nutrition_agent,
                fitness_agent=fitness_agent,
                delegations=delegations,
                user_profile=user_profile,
                image_path=image_path,
            )

        try:
            final_text, _responses = await asyncio.to_thread(_run_sync)
        except Exception as exc:
            await message.reply(f"Error running agents: {exc}")
            return
        finally:
            if image_path and image_path.exists():
                try:
                    image_path.unlink()
                except Exception:
                    pass

        for chunk in _chunk_message(final_text):
            await message.reply(chunk)


def main() -> None:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    cfg = DiscordBotConfig.from_env()
    bot = HealthButlerDiscordBot(cfg)
    bot.run(cfg.token)


if __name__ == "__main__":
    main()

