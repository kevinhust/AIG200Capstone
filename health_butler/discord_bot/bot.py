"""
Personal Health Butler Discord Bot

Main entry point for Discord Bot deployment on Google Cloud Run.
Integrates HealthSwarm for message processing with persistent Gateway connection.
"""

import asyncio
import logging
import os
import json
import re
from datetime import datetime, time
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

import discord
from discord import Intents, Client, Embed
from discord.ext import commands, tasks

from health_butler.swarm import HealthSwarm
from health_butler.discord_bot.profile_db import get_profile_db, ProfileDB
from aiohttp import web

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_ACTIVITY = os.getenv("DISCORD_ACTIVITY", "Helping with nutrition & fitness")

# Vaughan, Ontario → America/Toronto
LOCAL_TZ = ZoneInfo("America/Toronto")

# Demo Mode State (Global) - Pure in-memory, no persistence
demo_mode = False
demo_user_id = None
demo_guild_id = None

# Temporary demo user profile (in-memory only, cleared on exit)
_demo_user_profile: Dict[str, Any] = {}  # user_id -> temporary profile JSON

# Supabase Profile Database
profile_db: Optional[ProfileDB] = None

# In-memory cache for user profiles (synced with Supabase)
_user_profiles_cache: Dict[str, Dict[str, Any]] = {}  # user_id -> profile


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Get user profile from cache or load from Supabase."""
    global _user_profiles_cache, profile_db

    if user_id in _user_profiles_cache:
        return _user_profiles_cache[user_id]

    # Try to load from Supabase
    if profile_db:
        profile = profile_db.get_profile(user_id)
        if profile:
            # Convert Supabase format back to internal format
            _user_profiles_cache[user_id] = {
                "name": profile.get("full_name", ""),
                "age": profile.get("age", 25),
                "gender": profile.get("gender", "Not specified"),
                "height": profile.get("height_cm", 170),
                "weight": profile.get("weight_kg", 70),
                "goal": profile.get("goal", "General Health"),
                "conditions": profile.get("restrictions", "").split(", ") if profile.get("restrictions") else [],
                "activity": profile.get("activity", "Moderately Active"),
                "diet": profile.get("diet", []).split(", ") if profile.get("diet") else [],
                "meals": []
            }
            return _user_profiles_cache[user_id]

    # Return empty default if not found
    return {"meals": []}


def save_user_profile(user_id: str, profile: Dict[str, Any]) -> bool:
    """Save user profile to Supabase."""
    global profile_db, _user_profiles_cache

    if not profile_db:
        logger.warning("ProfileDB not initialized, skipping save")
        return False

    try:
        # Check if profile exists
        existing = profile_db.get_profile(user_id)

        conditions = profile.get("conditions", [])
        restrictions_str = ", ".join(conditions) if conditions and "None" not in conditions else None

        profile_data = {
            "id": user_id,
            "full_name": profile.get("name", ""),
            "age": int(profile.get("age", 25)),
            "weight_kg": float(profile.get("weight", 70)),
            "height_cm": float(profile.get("height", 170)),
            "goal": profile.get("goal", "General Health"),
            "restrictions": restrictions_str
        }

        if existing:
            profile_db.update_profile(user_id, **profile_data)
        else:
            profile_db.create_profile(
                discord_user_id=user_id,
                full_name=profile.get("name", ""),
                age=int(profile.get("age", 25)),
                gender=profile.get("gender", "Not specified"),
                height_cm=float(profile.get("height", 170)),
                weight_kg=float(profile.get("weight", 70)),
                goal=profile.get("goal", "General Health"),
                conditions=conditions,
                activity=profile.get("activity", "Moderately Active"),
                diet=profile.get("diet", [])
            )

        # Update cache
        _user_profiles_cache[user_id] = profile
        logger.info(f"✅ Profile saved for user {user_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to save profile: {e}")
        return False


def calculate_daily_target(profile: Dict[str, Any]) -> int:
    """Calculate TDEE based on Mifflin-St Jeor Equation."""
    try:
        weight = float(profile.get('weight_kg', 70))
        height = float(profile.get('height_cm', 170))
        age = int(profile.get('age', 30))
        gender = profile.get('gender', 'Male').lower()
        
        # BMR
        bmr = (10 * weight) + (6.25 * height) - (5 * age)
        if 'female' in gender:
            bmr -= 161
        else:
            bmr += 5
        
        # Activity Factor
        activity_map = {
            "sedentary": 1.2,
            "lightly active": 1.375,
            "moderately active": 1.55,
            "very active": 1.725,
            "extra active": 1.9
        }
        factor = activity_map.get(profile.get('activity', '').lower(), 1.2)
        tdee = bmr * factor
        
        # Goal adjustment
        goal = profile.get('goal', '').lower()
        if 'lose' in goal:
            tdee -= 500
        elif 'gain' in goal:
            tdee += 300
            
        return int(tdee)
    except Exception as e:
        logger.warning(f"Failed to calculate TDEE: {e}")
        return 2000


def save_demo_profile(user_id: str, profile: Dict[str, Any]) -> bool:
    """Save demo user profile to Supabase (wrapper for save_user_profile).
    
    Added by Research Agent on 2026-02-12 to fix undefined function error.
    """
    return save_user_profile(user_id, profile)


class LogWorkoutView(discord.ui.View):
    """Refined Interactive buttons for Fitness Agent recommendations."""
    def __init__(self, data: Dict[str, Any]):
        super().__init__(timeout=None)
        self.data = data
        self.recommendations = data.get("recommendations", [])

    @discord.ui.button(label='Log Workout', style=discord.ButtonStyle.green, emoji='💪')
    async def log_workout(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"🎯 **Activity Logged!**\nGoal: {self.recommendations[0]['name'] if self.recommendations else 'Exercise'}\nKeep up the great work!",
            ephemeral=True
        )

    @discord.ui.button(label='More Options', style=discord.ButtonStyle.gray, emoji='🔄')
    async def more_options(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🔄 Searching for alternative exercises that match your profile...",
            ephemeral=True
        )

    @discord.ui.button(label='Safety Info', style=discord.ButtonStyle.red, emoji='🛡️')
    async def safety_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        warnings = self.data.get("safety_warnings", [])
        msg = "**Safety Details**:\n" + ("\n".join([f"- {w}" for w in warnings]) if warnings else "No specific restrictions noted for this request.")
        await interaction.response.send_message(msg, ephemeral=True)


class DietSelectView(discord.ui.View):
    """Step 5: Dietary Preferences Multi-Select View"""
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.select(
        placeholder="Select Dietary Preferences...",
        min_values=0,
        max_values=5,
        options=[
            discord.SelectOption(label="No Restrictions", emoji="✅", value="None"),
            discord.SelectOption(label="Vegetarian", emoji="🥗", value="Vegetarian"),
            discord.SelectOption(label="Vegan", emoji="🌱", value="Vegan"),
            discord.SelectOption(label="Keto", emoji="🥓", value="Keto"),
            discord.SelectOption(label="Gluten-Free", emoji="🌾", value="Gluten-Free"),
            discord.SelectOption(label="Dairy-Free", emoji="🥛", value="Dairy-Free"),
        ]
    )
    async def select_diet(self, interaction: discord.Interaction, select: discord.ui.Select):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This setup is for someone else!", ephemeral=True)

        global demo_mode, _demo_user_profile, demo_user_id
        user_id = str(interaction.user.id)

        # Update existing profile (don't overwrite!)
        if user_id not in _demo_user_profile:
            _demo_user_profile[user_id] = {"meals": []}
        _demo_user_profile[user_id]["diet"] = select.values
        if "meals" not in _demo_user_profile[user_id]:
            _demo_user_profile[user_id]["meals"] = []

        demo_mode = True
        demo_user_id = user_id

        # Save to Supabase
        save_user_profile(demo_user_id, _demo_user_profile[user_id])

        profile = _demo_user_profile[user_id]
        summary = (
            "🎉 **Registration Complete!**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👤 **Profile Ready** (Persisted to Database)\n"
            f"• Name: `{profile.get('name', 'N/A')}`\n"
            f"• Age: `{profile.get('age', 'N/A')}` | Gender: `{profile.get('gender', 'N/A')}`\n"
            f"• Metrics: `{profile.get('height', 'N/A')}cm / {profile.get('weight', 'N/A')}kg`\n"
            f"• Goal: `{profile.get('goal', 'N/A')}`\n"
            f"• Conditions: `{', '.join(profile.get('conditions', [])) or 'None'}`\n"
            f"• Activity: `{profile.get('activity', 'N/A')}`\n"
            f"• Diet: `{', '.join(profile.get('diet', [])) or 'None'}`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💾 **Your profile is saved!** Data persists across sessions.\n\n"
            "✨ You can now ask health questions or upload food photos!"
        )
        await interaction.response.edit_message(content=summary, view=None)

        await interaction.client.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="[Demo Mode] " + DISCORD_ACTIVITY
            )
        )
        logger.info(f"✅ Full Demo registration complete for {interaction.user.display_name}")


class ActivitySelectView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.select(
        placeholder="Select Activity Level...",
        options=[
            discord.SelectOption(label="Sedentary", description="Desk job, little exercise", emoji="🪑"),
            discord.SelectOption(label="Lightly Active", description="1-3 days/week exercise", emoji="🚶"),
            discord.SelectOption(label="Moderately Active", description="3-5 days/week exercise", emoji="🏃"),
            discord.SelectOption(label="Very Active", description="6-7 days/week exercise", emoji="🏋️"),
            discord.SelectOption(label="Extra Active", description="Physical job + training", emoji="🔥"),
        ]
    )
    async def select_activity(self, interaction: discord.Interaction, select: discord.ui.Select):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This setup is for someone else!", ephemeral=True)

        global _demo_user_profile
        _demo_user_profile[self.user_id]["activity"] = select.values[0]
        await interaction.response.edit_message(
            content="**Step 5/5: Dietary Preferences**\nSelect any dietary restrictions or preferences:",
            view=DietSelectView(self.user_id)
        )


class ConditionSelectView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.select(
        placeholder="Select Health Conditions...",
        min_values=0,
        max_values=4,
        options=[
            discord.SelectOption(label="No Conditions", emoji="✅", value="None"),
            discord.SelectOption(label="Knee Injury / Pain", emoji="🦵", value="Knee Injury"),
            discord.SelectOption(label="High Blood Pressure", emoji="💓", value="Hypertension"),
            discord.SelectOption(label="Diabetes", emoji="🩸", value="Diabetes"),
            discord.SelectOption(label="Lower Back Pain", emoji="🔙", value="Lower Back Pain"),
        ]
    )
    async def select_conditions(self, interaction: discord.Interaction, select: discord.ui.Select):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This setup is for someone else!", ephemeral=True)

        global _demo_user_profile
        _demo_user_profile[self.user_id]["conditions"] = select.values if "None" not in select.values else []
        await interaction.response.edit_message(
            content="**Step 4/5: Activity Level**\nHow active are you on a weekly basis?",
            view=ActivitySelectView(self.user_id)
        )


class GoalSelectView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.select(
        placeholder="Select Health Goal...",
        options=[
            discord.SelectOption(label="Lose Weight", description="Calorie deficit focus", emoji="📉"),
            discord.SelectOption(label="Maintain", description="Balanced nutrition focus", emoji="⚖️"),
            discord.SelectOption(label="Gain Muscle", description="Calorie surplus/protein focus", emoji="📈"),
        ]
    )
    async def select_goal(self, interaction: discord.Interaction, select: discord.ui.Select):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This setup is for someone else!", ephemeral=True)

        global _demo_user_profile
        _demo_user_profile[self.user_id]["goal"] = select.values[0]
        await interaction.response.edit_message(
            content="**Step 3/5: Health Conditions**\n(Phase 5 Safety Integration) Select any conditions to enable safety filtering:",
            view=ConditionSelectView(self.user_id)
        )


class HealthProfileModal(discord.ui.Modal, title='Step 1/5: Basic Information'):
    user_name = discord.ui.TextInput(label='Name', placeholder='Kevin Wang', min_length=2, max_length=50)
    age = discord.ui.TextInput(label='Age (18-100)', placeholder='35', min_length=1, max_length=3)
    gender = discord.ui.TextInput(label='Gender', placeholder='Male / Female', min_length=1, max_length=10)
    height = discord.ui.TextInput(label='Height (cm)', placeholder='175', min_length=2, max_length=3)
    weight = discord.ui.TextInput(label='Weight (kg)', placeholder='90', min_length=2, max_length=3)

    async def on_submit(self, interaction: discord.Interaction):
        global _demo_user_profile
        user_id = str(interaction.user.id)

        # Initialize temporary demo profile in memory
        _demo_user_profile[user_id] = {
            "name": self.user_name.value,
            "age": int(self.age.value),
            "gender": self.gender.value,
            "height": float(self.height.value),
            "weight": float(self.weight.value),
            "meals": []
        }
        await interaction.response.send_message(
            "✅ Basic information saved.\n\n**Step 2/5: Health Goal**\nWhat is your primary objective?",
            view=GoalSelectView(user_id)
        )


class StartSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Start Setup', style=discord.ButtonStyle.green, emoji='🚀')
    async def start_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(HealthProfileModal())


class HealthButlerDiscordBot(Client):
    def __init__(self):
        global profile_db

        intents = Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True

        super().__init__(intents=intents, heartbeat_timeout=120)

        # Initialize Supabase ProfileDB
        try:
            profile_db = get_profile_db()
            logger.info("✅ Supabase ProfileDB initialized")
        except Exception as e:
            logger.warning(f"⚠️ ProfileDB init failed (continuing without persistence): {e}")
            profile_db = None

        self.swarm = HealthSwarm(verbose=True)
        self.start_time = datetime.now()
        logger.info("Health Butler Discord Bot initialized")

    @tasks.loop(time=[time(7, 30, tzinfo=LOCAL_TZ), time(20, 0, tzinfo=LOCAL_TZ)])
    async def daily_summary_loop(self):
        """Phase 7 Refinement: Proactive Daily Summaries with Timezone."""
        global demo_mode, demo_user_id
        if demo_mode and demo_user_id:
            try:
                user = await self.fetch_user(int(demo_user_id))
                if user:
                    now = datetime.now(LOCAL_TZ)
                    if now.hour < 12:
                        msg = "☀️ **Good Morning!**\nTime for a healthy breakfast. Today's goal: Stay within your calorie target!"
                    else:
                        msg = "🌙 **Evening Summary**\nYou've done great today! Suggested evening activity: 15min light stretching."
                    await user.send(msg)
                    logger.info(f"📬 Sent daily summary to {user.display_name}")
            except Exception as e:
                logger.error(f"Failed to send scheduled summary: {e}")

    async def setup_hook(self):
        logger.info("Bot setup_hook executed: starting summary loop")
        self.daily_summary_loop.start()
        # Start health check server within the loop
        asyncio.create_task(self._start_health_server())

    async def _start_health_server(self):
        """Minimal HTTP server for Cloud Run health checks."""
        app = web.Application()
        app.router.add_get('/health', lambda r: web.Response(text="OK"))
        port = int(os.getenv("PORT", 8080))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"❤️ Health check server started on port {port}")

    async def on_ready(self):
        logger.info(f"✅ Bot logged in as {self.user} (ID: {self.user.id})")

    async def on_message(self, message: discord.Message):
        global demo_mode, demo_user_id
        if message.author.bot or not message.guild: return

        # Helper for user_id in later scopes
        author_id = str(message.author.id)

        if message.content.strip().lower().startswith("/demo"):
            await self._handle_demo_command(message)
            return

        if message.content.strip().lower() in ("/exit", "/quit"):
            if demo_mode: await self._handle_exit_command(message)
            else: await message.channel.send("⚠️ Use `/demo` first.")
            return

        if demo_mode and str(message.author.id) != demo_user_id: return

        # Load temporary demo profile from memory
        global _demo_user_profile
        user_profile = _demo_user_profile.get(str(message.author.id), {"meals": []})

        try:
            image_attachment = next((a for a in message.attachments if a.content_type and a.content_type.startswith('image/')), None)
            user_context = {
                "user_id": str(message.author.id),
                "username": message.author.display_name,
                "conditions": user_profile.get("conditions", []),
                "goal": user_profile.get("goal", "General Health"),
                "activity": user_profile.get("activity", "Moderately Active"),
                "daily_intake": user_profile.get("meals", [])
            }

            async with message.channel.typing():
                # Run sync swarm execution in a thread to keep Discord heartbeat alive
                loop = asyncio.get_event_loop()
                if image_attachment:
                    image_path = f"/tmp/{image_attachment.filename}"
                    await image_attachment.save(image_path)
                    result = await asyncio.to_thread(
                        self.swarm.execute, 
                        user_input="Analyze this meal", 
                        image_path=image_path, 
                        user_context=user_context
                    )
                    os.remove(image_path)
                else:
                    result = await asyncio.to_thread(
                        self.swarm.execute, 
                        user_input=message.content, 
                        user_context=user_context
                    )

                # Persist Meal data using the structured response
                latest_meal = await self._persist_meal_data(result['response'], str(message.author.id))

                await self._send_swarmed_response(message.channel, result['response'], str(message.author.id), latest_meal=latest_meal)

        except Exception as e:
            logger.error(f"Error: {e}")
            await message.channel.send(f"⚠️ Error: {str(e)}")

    async def _send_swarmed_response(self, channel, response: str, interaction_user_id: str, latest_meal: Optional[Dict[str, Any]] = None):
        try:
            clean_str = response.strip()
            # Improved robust JSON extraction
            json_pattern = re.compile(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', re.DOTALL)
            match = json_pattern.search(clean_str)
            
            data = None
            if match:
                try:
                    data = json.loads(match.group(1))
                except Exception as je:
                    logger.debug(f"Inner JSON parse failed: {je}")
            
            if not data:
                try:
                    data = json.loads(clean_str)
                except:
                    pass

            # If we have structured data, use the Unified Embed Design
            if isinstance(data, dict):
                # Check if it's a Nutrition analysis
                if "dish_name" in data and "total_macros" in data:
                    embed = self._build_nutrition_embed(data)
                    await channel.send(embed=embed)
                else:
                    # Fallback for other specialist agents or generic JSON
                    embed = Embed(title="💎 Health Butler Analysis", color=discord.Color.blue())
                    for k, v in data.items():
                        if isinstance(v, (str, int, float)) and len(str(v)) < 1000:
                            embed.add_field(name=k.replace("_", " ").title(), value=str(v), inline=False)
                    await channel.send(embed=embed)
                
                # Show Today's Summary with direct injection to bypass DB latency
                await self._send_daily_summary_embed(channel, str(interaction_user_id), latest_meal=latest_meal)
                return

            # Fallback for text-only responses
            MAX_LEN = 1900
            if len(clean_str) > MAX_LEN:
                for i in range(0, len(clean_str), MAX_LEN):
                    await channel.send(clean_str[i:i+MAX_LEN])
            else:
                await channel.send(clean_str)

        except Exception as e:
            logger.error(f"Response handling error: {e}")
            await channel.send(f"⚠️ Error processing response: {str(e)[:100]}")

    def _build_nutrition_embed(self, data: Dict[str, Any]) -> Embed:
        """
        Build a premium, standardized nutrition embed based on user-provided design.
        """
        dish = data.get("dish_name", "Unknown Meal")
        macros = data.get("total_macros", {})
        dt = data.get("detailed_nutrients", {})
        confidence = data.get("confidence_score", 0.9)
        
        stars = "★" * min(5, max(0, int(confidence * 5))) + "☆" * (5 - min(5, max(0, int(confidence * 5))))
        title = f"Nutrition Analysis: {dish} • {int(confidence*100)}% Confidence"
        embed = Embed(title=title, color=discord.Color.green())

        cals = macros.get("calories", 0)
        p = macros.get("protein", 0)
        c = macros.get("carbs", 0)
        f = macros.get("fat", 0)
        
        embed.description = f"🔥 **{cals}** kcal | 🍖 **{p}g** P | 🍞 **{c}g** C | 🥑 **{f}g** F"

        total_g = p + c + f
        if total_g > 0:
            def get_bar(val):
                pct = int((val / total_g) * 20)
                return "█" * pct + "░" * (20 - pct)
            
            p_pct = (p / total_g) * 100
            c_pct = (c / total_g) * 100
            f_pct = (f / total_g) * 100
            
            breakdown = (
                f"🍖 **Protein** {p_pct:2.0f}% `{get_bar(p)}`\n"
                f"🍞 **Carbs**   {c_pct:2.0f}% `{get_bar(c)}`\n"
                f"🥑 **Fat**     {f_pct:2.0f}% `{get_bar(f)}`"
            )
            embed.add_field(name="📊 Macros Breakdown", value=breakdown, inline=False)

        details = [
            f"• Calories: {cals} kcal",
            f"• Protein: {p}g",
            f"• Total Fat: {f}g (Sat: ~{dt.get('saturated_fat_g', '?')}g*)",
            f"• Carbs: {c}g (Fiber: ~{dt.get('fiber_g', '?')}g*, Sugars: ~{dt.get('sugar_g', '?')}g*)",
            f"• Sodium: ~{dt.get('sodium_mg', '?')}mg*"
        ]
        embed.add_field(name="📋 Detailed Nutrition", value="\n".join(details), inline=True)

        ingredients = data.get("ingredients_with_portions", [])
        if not ingredients: ingredients = data.get("items_detected", [])
        
        ing_list = "\n".join([f"• {i}" for i in ingredients[:6]]) if ingredients else "Not specified"
        embed.add_field(name="🥗 Key Ingredients", value=ing_list, inline=True)

        insight = data.get("health_tip") or data.get("composition_analysis", "Maintain a balanced diet!")
        embed.add_field(name="💡 Health Insight", value=insight, inline=False)

        embed.set_footer(text=f"Confidence: {stars} ({int(confidence*100)}%) • Anchored to USDA data + visual estimation")
        return embed

    async def _send_daily_summary_embed(self, channel, user_id: str, latest_meal: Optional[Dict[str, Any]] = None):
        """Send a 'Today's Summary' embed as requested by user."""
        if not profile_db or not user_id: return
        
        try:
            profile = get_user_profile(user_id)
            stats = profile_db.get_today_stats(user_id)
            target = calculate_daily_target(profile)
            
            consumed = stats["total_calories"]
            meals_count = stats["meal_count"]
            
            # Direct Injection Logic: If summary doesn't yet include the latest meal, add it.
            # This happens due to eventual consistency or write propagation delay.
            if latest_meal and latest_meal.get("macros", {}).get("calories"):
                # Check if this meal is already accounted for in stats (simple heuristic: if stats is 0 but we have a meal, it's definitely missing)
                if consumed < latest_meal["macros"]["calories"]:
                    consumed += latest_meal["macros"]["calories"]
                    meals_count += 1
                    logger.info("💉 Injected latest meal into summary to bypass DB latency")

            percent = (consumed / target * 100) if target > 0 else 0
            remaining = target - consumed
            
            embed = Embed(title="🟢 Today's Summary", color=discord.Color.green())
            embed.add_field(
                name="📊 Calories", 
                value=f"**{consumed}** / {target} kcal ({percent:.1f}%)", 
                inline=False
            )
            embed.add_field(name="🍽️ Meals", value=f"**{meals_count}**", inline=True)
            
            if remaining > 0:
                embed.add_field(name="💡 Status", value=f"You can have about **{remaining}** more kcal", inline=False)
            else:
                embed.add_field(name="⚠️ Status", value=f"Over target by **{abs(remaining)}** kcal", inline=False)
                
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to send daily summary: {e}")

    async def _persist_meal_data(self, response: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Extract and persist meal data - in-memory for demo, Supabase for real users."""
        try:
            clean_str = response.strip()
            if "```json" in clean_str: clean_str = clean_str.split("```json")[-1].split("```")[0].strip()
            elif "```" in clean_str: clean_str = clean_str.split("```")[-1].split("```")[0].strip()
            data = json.loads(clean_str)

            if "dish_name" in data and "total_macros" in data:
                m = data["total_macros"]
                meal_record = {
                    "time": datetime.now(LOCAL_TZ).strftime("%H:%M"),
                    "dish": data["dish_name"],
                    "macros": data["total_macros"]
                }

                global demo_mode, _demo_user_profile, profile_db

                # Demo mode: in-memory only
                if demo_mode and user_id == demo_user_id:
                    if user_id not in _demo_user_profile:
                        _demo_user_profile[user_id] = {"meals": []}
                    _demo_user_profile[user_id].setdefault("meals", []).append(meal_record)
                    logger.info(f"📝 Demo meal saved: {data['dish_name']}")

                # Real user: persist to Supabase
                elif profile_db:
                    from datetime import date
                    today = date.today()
                    calories = m.get('calories', 0)
                    protein = m.get('protein', 0)
                    carbs = m.get('carbs', 0)
                    fat = m.get('fat', 0)

                    # 1. Create or update daily summary log
                    profile_db.create_daily_log(
                        discord_user_id=user_id,
                        log_date=today,
                        calories_intake=calories,
                        protein_g=protein
                    )

                    # 2. Create detailed meal record
                    profile_db.create_meal(
                        discord_user_id=user_id,
                        dish_name=data["dish_name"],
                        calories=calories,
                        protein_g=protein,
                        carbs_g=carbs,
                        fat_g=fat,
                        confidence_score=data.get("confidence_score") or data.get("total_confidence", 0.0)
                    )
                    logger.info(f"💾 Detailed meal persisted to DB: {data['dish_name']} ({calories} kcal)")

                    # Also update local cache
                    if user_id in _user_profiles_cache:
                        _user_profiles_cache[user_id].setdefault("meals", []).append(meal_record)

        except Exception as e:
            logger.debug(f"Meal persist error: {e}")

    async def _handle_demo_command(self, message):
        global demo_mode, demo_user_id, demo_user_profile
        if not demo_mode:
            # Check if user already has a profile
            user_id = str(message.author.id)
            existing_profile = get_user_profile(user_id)

            if existing_profile and existing_profile.get("name"):
                # User exists, activate demo mode directly
                demo_mode = True
                demo_user_id = user_id
                _demo_user_profile[user_id] = existing_profile

                await message.channel.send(
                    f"👋 Welcome back, **{existing_profile.get('name', 'User')}**!\n"
                    f"Your profile has been loaded from database.\n"
                    f"Goal: {existing_profile.get('goal', 'General Health')}\n"
                    "You can now ask health questions or upload food photos!"
                )
            else:
                # Always start fresh registration flow
                await message.channel.send(
                    "Hi! I'm **Health Butler**. Let's set up your profile for safety-first health advice.",
                    view=StartSetupView()
                )

    async def _handle_exit_command(self, message):
        global demo_mode, demo_user_id, _demo_user_profile
        user_id = str(message.author.id)

        demo_mode = False
        demo_user_id = None

        # Clear this user's temporary demo profile
        if user_id in _demo_user_profile:
            del _demo_user_profile[user_id]
            logger.info(f"🗑️ Cleared demo profile for user {user_id}")

        await message.channel.send("🛑 **Exited Demo Mode**")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=DISCORD_ACTIVITY))

def main():
    bot = HealthButlerDiscordBot()
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        logger.error("No DISCORD_TOKEN found.")

if __name__ == "__main__":
    main()
