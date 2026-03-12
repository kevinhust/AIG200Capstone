import logging
import discord
import random
import json
import os
from typing import Dict, Any, Optional, List
from src.discord_bot import profile_utils as pu
from src.discord_bot.modals import RegistrationModal
from src.discord_bot.views import RegistrationViewA, StartSetupView

logger = logging.getLogger(__name__)

# Cache for exercises with images
_exercises_with_images: Optional[List[Dict]] = None

def _load_exercises_with_images() -> List[Dict]:
    """Load exercises that have image URLs from cache."""
    global _exercises_with_images
    if _exercises_with_images is not None:
        return _exercises_with_images

    # Try multiple possible paths (Docker container vs local development)
    possible_paths = [
        "/app/data/rag/exercise_cache.json",  # Docker container
        "data/rag/exercise_cache.json",        # Local development
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "rag", "exercise_cache.json"),
    ]

    for cache_path in possible_paths:
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                all_exercises = cache_data.get('data', [])
                _exercises_with_images = [ex for ex in all_exercises if ex.get('image_url')]
                logger.info(f"📦 Loaded {len(_exercises_with_images)} exercises with images from {cache_path}")
                return _exercises_with_images

    logger.warning(f"⚠️ Exercise cache not found. Tried: {possible_paths}")
    return []

async def _on_registration_modal_submit(interaction: discord.Interaction, data: Dict[str, Any], HealthButlerEmbed):
    """Callback for v4.1 simplified RegistrationModal (Step 1/3)"""
    user_id = str(interaction.user.id)
    
    # Initialize/Update profile buffer with metrics
    pu._demo_user_profile[user_id] = {
        "name": data["name"],
        "age": data["age"],
        "height_cm": data["height_cm"],
        "weight_kg": data["weight_kg"],
        "meals": []
    }
    
    # Send Progress Embed (Step 2/3 🟢🟢⚪) and RegistrationViewA
    embed = HealthButlerEmbed.build_progress_embed(
        step=2,
        total_steps=3,
        title="Biological Profile",
        description=(
            f"Thanks **{data['name']}**! We've noted your metrics.\n"
            "Now, please select your **Biological Sex**, **Health Goal**, and **Activity Level** to calibrate your plan.\n\n"
            "🛡️ *Privacy Hint: Your data is stored securely and only used for your health analysis.*"
        )
    )
    
    # Instantiate the new modular view
    view = RegistrationViewA(user_id, pu._demo_user_profile[user_id], HealthButlerEmbed)
    
    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )

async def handle_reset_command(message: discord.Message, HealthButlerEmbed, OnboardingGreetingView):
    """♻️ Reset user profile and cache."""
    logger.info(f"♻️ Reset requested by {message.author}")
    author_id = str(message.author.id)
    
    # 1. Clear DB
    db = pu.profile_db
    deleted = False
    if db is not None:
        deleted = db.delete_profile(author_id)
    
    # 2. Clear Local Cache
    cache_cleared = False
    if author_id in pu._user_profiles_cache:
        del pu._user_profiles_cache[author_id]
        cache_cleared = True
    if author_id in pu._demo_user_profile:
        del pu._demo_user_profile[author_id]
        cache_cleared = True
    
    # Consider success if either DB deletion succeeded, cache was cleared, or DB is not configured (demo mode).
    if deleted or cache_cleared or db is None:
        embed = HealthButlerEmbed.welcome_embed(message.author.display_name)
        embed.title = "♻️ Profile Reset Successful"
        embed.description = "Your health profile has been completely cleared. You can start fresh whenever you're ready!\n\nClick the button below to begin your new journey."
        
        # Wrapped callback to inject HealthButlerEmbed
        async def on_submit_wrapper(interaction, data):
            await _on_registration_modal_submit(interaction, data, HealthButlerEmbed)

        view = OnboardingGreetingView(
            on_registration_submit=on_submit_wrapper,
            embed_factory=HealthButlerEmbed
        )
        await message.reply(embed=embed, view=view)
    else:
        # DB deletion failed, and there was no cache to clear
        await message.reply("❌ Failed to reset profile. Please try again later or contact support.")

async def handle_settings_command(message: discord.Message):
    """⚙️ Manages personalized engagement settings."""
    author_id = str(message.author.id)
    content = message.content.replace("/settings", "").strip().lower()
    
    # Fetch profile
    profile = pu._user_profiles_cache.get(author_id) or pu.get_user_profile(author_id) or {}
    prefs = profile.get("preferences_json", {})
    
    if not content:
        status_ico = "✅ Enabled" if prefs.get("morning_checkin_enabled", True) else "❌ Disabled"
        await message.reply(
            f"⚙️ **Your Health Assistant Settings**\n"
            f"• Morning Check-in: **{status_ico}**\n\n"
            f"To toggle, use `/settings morning on` or `/settings morning off`."
        )
        return

    if "morning" in content:
        new_val = "off" not in content
        prefs["morning_checkin_enabled"] = new_val
        if pu.profile_db:
            pu.profile_db.update_profile(author_id, preferences_json=prefs)
        
        # Update cache
        if author_id in pu._user_profiles_cache:
            pu._user_profiles_cache[author_id]["preferences_json"] = prefs
        
        status_text = "enabled" if new_val else "disabled"
        await message.reply(f"✅ Morning Check-in successfully **{status_text}**.")

async def handle_demo_command(message: discord.Message):
    """👋 Handle /demo command logic."""
    if not pu.demo_mode:
        user_id = str(message.author.id)
        existing_profile = pu.get_user_profile(user_id)

        if existing_profile and existing_profile.get("name"):
            pu.demo_mode = True
            pu.demo_user_id = user_id
            pu._demo_user_profile[user_id] = existing_profile

            await message.channel.send(
                f"👋 Welcome back, **{existing_profile.get('name', 'User')}**!\n"
                f"Your profile has been loaded from database.\n"
                f"Goal: {existing_profile.get('goal', 'General Health')}\n"
                "You can now ask health questions or upload food photos!"
            )
        else:
            async def on_submit_wrapper(interaction, data):
                from src.discord_bot.embed_builder import HealthButlerEmbed
                await _on_registration_modal_submit(interaction, data, HealthButlerEmbed)

            await message.channel.send(
                "Hi! I'm **Health Butler**. Let's set up your profile for safety-first health advice.",
                view=StartSetupView(on_submit_callback=on_submit_wrapper)
            )

async def handle_exit_command(message: discord.Message):
    """🚪 Exit demo mode."""
    user_id = str(message.author.id)
    pu.demo_mode = False
    pu.demo_user_id = None
    if user_id in pu._demo_user_profile:
        del pu._demo_user_profile[user_id]
        logger.info(f"🗑️ Cleared demo profile for user {user_id}")
    await message.reply("Demo mode exited. Your session data has been cleared.")


async def handle_help_command(message: discord.Message, HealthButlerEmbed):
    """📖 Segmented help command based on user journey."""
    user_id = str(message.author.id)
    profile = pu.get_user_profile(user_id)
    
    embed = HealthButlerEmbed.create_base_embed(
        title="📖 Health Butler Help Center",
        description="Welcome to your personal health assistant. Here's how you can make the most of my features.",
        color=discord.Color.blue()
    )
    
    # 1. New Users / Setup
    embed.add_field(
        name="🐣 Getting Started",
        value=(
            "`/setup` - Begin your health onboarding.\n"
            "`/demo` - Try Butler with temporary data."
        ),
        inline=False
    )
    
    # 2. Daily Tracking
    embed.add_field(
        name="🍱 Daily Tracking",
        value=(
            "**Upload a photo** of your meal for instant macro analysis.\n"
            "**Type 'Summary'** to see your current calorie budget.\n"
            "**Type 'Who am I?'** to view your active profile."
        ),
        inline=False
    )
    
    # 3. Advanced Features
    embed.add_field(
        name="🏋️ Advanced Features",
        value=(
            "`/trends` - View your 30-day health analytics.\n"
            "`/roulette` - Spin for meal inspiration 🎰.\n"
            "`/test_nudge [exercise]` - Preview a visual workout reminder (v7.1).\n"
            "`/settings` - Manage notifications."
        ),
        inline=False
    )
    
    # 4. Privacy & Support
    embed.add_field(
        name="🛡️ Privacy & Security",
        value=(
            "Talk to me in **Direct Messages** for private tracking.\n"
            "`/reset` - Permanently delete your data."
        ),
        inline=False
    )
    
    embed.set_footer(text="Health Butler v7.0 | Clean Architecture")
    await message.reply(embed=embed)

async def handle_test_nudge_command(
    message: discord.Message,
    HealthButlerEmbed,
    ProactiveNudgeView,
    exercise_name: Optional[str] = None
):
    """
    🧪 Test command for visualizing a proactive nudge with exercise image.

    Usage:
        /test_nudge          - Random exercise with image
        /test_nudge Yoga     - Specific exercise (if available)
    """
    exercises = _load_exercises_with_images()

    if not exercises:
        await message.reply("❌ No exercises with images available in cache.")
        return

    # Find exercise by name or pick random
    selected = None
    if exercise_name:
        # Case-insensitive search among exercises with images
        for ex in exercises:
            if exercise_name.lower() in ex.get('name', '').lower():
                selected = ex
                break

        if not selected:
            # No match with image - notify user and pick random
            await message.reply(
                f"⚠️ No exercise matching '**{exercise_name}**' has an image. Showing a random exercise instead:"
            )
            selected = random.choice(exercises)
    else:
        selected = random.choice(exercises)

    # Extract exercise data
    name = selected.get('name', 'Exercise')
    image_url = selected.get('image_url')
    met_value = selected.get('met_value', 3.5)
    intensity = selected.get('intensity', 'moderate')
    equipment = selected.get('equipment_type', 'bodyweight')

    # Build mock time window and budget for demo
    mock_time_window = {
        "day_name": "Tuesday",
        "hour_bucket": "evening",
        "confidence": 0.85,
        "frequency": 5
    }

    mock_budget = {
        "remaining": 350,
        "remaining_pct": 65,
        "status": "good",
        "status_emoji": "🟢",
        "calorie_bar": "🟢 `[██████░░░░] 65%`"
    }

    # Build the nudge embed with v7.1 visual enhancement
    embed = HealthButlerEmbed.build_proactive_nudge_embed(
        user_name=message.author.display_name,
        exercise_name=name,
        time_window=mock_time_window,
        budget_progress=mock_budget,
        empathy_strategy=None,
        image_url=image_url,
        met_value=met_value,
        intensity=intensity
    )

    # Add equipment info as extra context
    embed.add_field(
        name="📋 Exercise Details",
        value=f"**Equipment**: {equipment.title()}\n**Cache ID**: {selected.get('id', 'N/A')}",
        inline=False
    )

    # Create view with feedback buttons
    view = ProactiveNudgeView(
        user_id=str(message.author.id),
        exercise_name=name
    )

    await message.reply(embed=embed, view=view)
    logger.info(f"🧪 Test nudge sent: {name} (MET: {met_value}, Image: {bool(image_url)})")
