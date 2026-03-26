import logging
import json
import discord
from typing import Dict, Any, Optional, List
from src.discord_bot import profile_utils as pu
from src.discord_bot.modals import RegistrationModal
from src.discord_bot.views import RegistrationViewA, StartSetupView
from src.agents.fitness.fitness_agent import FitnessAgent
from src.data_rag.simple_rag_tool import SimpleRagTool

logger = logging.getLogger(__name__)

async def _on_registration_modal_submit(interaction: discord.Interaction, data: Dict[str, Any], HealthButlerEmbed, bot=None):
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
    view = RegistrationViewA(bot, user_id, pu._demo_user_profile[user_id], HealthButlerEmbed)
    
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
    deleted = db.delete_profile(author_id)
    
    # 2. Clear Local Cache
    if author_id in pu._user_profiles_cache:
        del pu._user_profiles_cache[author_id]
    
    if deleted:
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
            "**Type 'Who am I?'** to view your active profile.\n"
            "`/fitness` - Get workout recommendations instantly."
        ),
        inline=False
    )

    # 3. Advanced Features
    embed.add_field(
        name="🏋️ Advanced Features",
        value=(
            "`/fitness [type]` - Workout plan (cardio, strength, yoga)\n"
            "`/trends` - View your 30-day health analytics.\n"
            "`/roulette` - Spin for meal inspiration 🎰.\n"
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


async def handle_routine_command(message: discord.Message):
    """📋 View user's current workout routine"""
    user_id = str(message.author.id)
    profile = pu.get_user_profile(user_id)

    if not profile or not profile.get("name"):
        await message.reply("⚠️ You don't have a profile yet. Run `/demo` to set up first.")
        return

    try:
        from src.discord_bot.profile_db import get_profile_db
        db = get_profile_db()

        if not db:
            await message.reply("⚠️ Database not connected.")
            return

        progress = db.get_workout_progress(user_id, days=30)
        routine_exercises = progress.get("routine_exercises", [])
        routine_count = progress.get("routine_count", 0)

        if not routine_exercises:
            embed = discord.Embed(
                title="📋 Your Workout Routine",
                description="No exercises in your routine yet.\n\nUse `/fitness` to get recommendations and add them!",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="💡 Tip",
                value="Click '📌 Add To Routine' on any workout recommendation to save it here.",
                inline=False
            )
        else:
            exercise_list = "\n".join([f"• **{ex}**" for ex in routine_exercises])
            embed = discord.Embed(
                title="📋 Your Workout Routine",
                description=f"You have **{routine_count}** exercise(s) in your routine.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Weekly Exercises",
                value=exercise_list,
                inline=False
            )
            embed.add_field(
                name="🎯 Target",
                value="~3 sessions per week for each exercise",
                inline=False
            )
            embed.add_field(
                name="📊 This Week",
                value=f"Completed: **{progress.get('completed_count', 0)}**\nTotal active: **{progress.get('total_minutes', 0)}** min",
                inline=False
            )

        await message.reply(embed=embed)

    except Exception as e:
        logger.error(f"Error in /routine command: {e}")
        await message.reply(f"⚠️ Failed to load routine: {str(e)[:100]}")


async def handle_fitness_command(
    message: discord.Message,
    HealthButlerEmbed,
    category: Optional[str] = None
):
    """🏋️ Handle /fitness command - direct fitness recommendations"""
    user_id = str(message.author.id)
    profile = pu.get_user_profile(user_id)

    if not profile or not profile.get("name"):
        await message.reply(
            "⚠️ You don't have a profile yet. Run `/demo` to set up first."
        )
        return

    # Build task based on category
    task = "Give me a workout plan"
    if category:
        # Map common category aliases
        category_map = {
            "cardio": "Cardio",
            "strength": "Strength",
            "flexibility": "Flexibility",
            "hiit": "HIIT",
            "stretch": "Stretching",
            "yoga": "Yoga",
        }
        normalized = category_map.get(category.lower(), category)
        task = f"Give me a {normalized} workout plan"

    # Get recent health memo from meals
    from src.discord_bot.profile_db import get_profile_db
    db = get_profile_db()

    visual_warnings = []
    try:
        # Get recent meals to check for recent food warnings (limit to last 5)
        meals = db.get_meals(user_id, limit=5) if db else []
        for meal in meals:
            warnings = meal.get("visual_warnings", [])
            if warnings:
                visual_warnings.extend(warnings)
    except Exception as e:
        logger.warning(f"Could not fetch recent meals for memo: {e}")

    # Add visual warnings to task if found
    if visual_warnings:
        task += f" (Note: Recent food warnings: {', '.join(set(visual_warnings))})"

    # Execute Fitness Agent (skip typing indicator to avoid 429)
    try:
        agent = FitnessAgent()
        context = [{"type": "user_context", "content": json.dumps({"user_id": user_id})}]

        # Run synchronously
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                result_str = await asyncio.to_thread(agent.execute, task, context)
            else:
                result_str = loop.run_until_complete(agent.execute_async(task, context))
        except RuntimeError:
            result_str = await agent.execute_async(task, context)

        # Parse JSON response - handle both raw JSON and markdown-wrapped JSON
        try:
            # Try direct parse first
            result = json.loads(result_str)
        except:
            # Clean up markdown code blocks if present
            cleaned = result_str.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[-1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[-1].split("```")[0].strip()
            try:
                result = json.loads(cleaned)
            except:
                result = {"summary": result_str[:500], "recommendations": []}

        # Build embed
        embed = HealthButlerEmbed.build_fitness_card(
            data=result,
            user_name=profile.get("name", "User"),
            budget_progress=result.get("budget_progress"),
            empathy_strategy=result.get("empathy_strategy"),
            user_habits=result.get("user_habits")
        )

        # Add category info if specified
        if category:
            embed.description += f"\n\n📂 Filter: **{category.upper()}**"

        # Add interactive view with buttons
        from src.discord_bot.views import LogWorkoutView
        view = LogWorkoutView(bot=None, data=result, user_id=user_id)

        await message.reply(embed=embed, view=view)

    except discord.HTTPException as e:
        if e.status == 429:
            logger.warning(f"Rate limited on fitness command, trying followup: {e}")
            # Fallback: send as new message instead of reply
            try:
                await message.channel.send(embed=embed, view=view)
            except:
                await message.channel.send(f"🏋️ Here's your workout plan: {result.get('summary', 'Generated')[:500]}")
        else:
            logger.error(f"HTTP error in /fitness command: {e}")
            await message.reply(f"⚠️ Error: {str(e)[:100]}")

    except Exception as e:
        logger.error(f"Error in /fitness command: {e}")
        await message.reply(f"⚠️ Failed to generate fitness plan: {str(e)[:100]}")
