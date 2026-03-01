"""
Personal Health Butler Discord Bot

Main entry point for Discord Bot deployment on Google Cloud Run.
Integrates HealthSwarm for message processing with persistent Gateway connection.
"""

import asyncio
import logging
import os
import json
from json import JSONDecoder
import re
import uuid
import discord
from discord import Client, Intents, Embed
from discord.ext import tasks
from datetime import datetime, time
from src.swarm import HealthSwarm
from src.discord_bot.embed_builder import HealthButlerEmbed
from src.discord_bot.views import RegistrationViewA, OnboardingGreetingView
from src.agents.engagement.engagement_agent import EngagementAgent
from src.agents.analytics.analytics_agent import AnalyticsAgent
from src.discord_bot.profile_db import get_profile_db
from src.discord_bot import profile_utils as pu
from src.discord_bot import intent_parser as ip
from src.discord_bot import commands as cmd
from typing import Optional, List, Dict, Any
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


# Logic moved to views.py, profile_utils.py, intent_parser.py, and commands.py





class HealthButlerDiscordBot(Client):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True

        super().__init__(intents=intents, heartbeat_timeout=120)

        # Initialize Supabase ProfileDB
        try:
            pu.profile_db = get_profile_db()
            logger.info("✅ Supabase ProfileDB initialized")
        except Exception as e:
            logger.warning(f"⚠️ ProfileDB init failed (continuing without persistence): {e}")
            pu.profile_db = None

        self.swarm = HealthSwarm(verbose=True)
        self.start_time = datetime.now()
        # Optional demo safety allowlists (comma-separated IDs). Empty => allow all.
        self.allowed_user_ids = pu._parse_int_set(os.getenv("DISCORD_ALLOWED_USER_IDS"))
        self.allowed_channel_ids = pu._parse_int_set(os.getenv("DISCORD_ALLOWED_CHANNEL_IDS"))
        self.engagement_agent = EngagementAgent()
        self.analytics_agent = AnalyticsAgent()
        logger.info("Health Butler Discord Bot initialized with Engagement and Analytics Agents")

    async def setup_hook(self):
        logger.info("Bot setup_hook: starting proactive loops")
        # Start loops
        if not self.morning_checkin.is_running():
            self.morning_checkin.start()
        if not self.nightly_summary.is_running():
            self.nightly_summary.start()
        
        # Start health check server within the loop
        asyncio.create_task(self._start_health_server())

    async def _send_proactive_message(self, user_id: str, embed: discord.Embed, view: Optional[discord.ui.View] = None):
        """Helper to send proactive DM to user if allowed."""
        try:
            profile = pu.get_user_profile(user_id)
            # Check privacy toggle
            prefs = profile.get("preferences", {})
            if not prefs.get("allow_proactive_notifications", True):
                return

            user = await self.fetch_user(int(user_id))
            if user:
                await user.send(embed=embed, view=view)
                logger.info(f"📬 Sent proactive message to {user.display_name}")
        except Exception as e:
            logger.error(f"Failed to send proactive message to {user_id}: {e}")

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
        logger.info(f"📡 Intents Status -> Message Content: {self.intents.message_content}, Guilds: {self.intents.guilds}, Messages: {self.intents.messages}")
        # Start proactive tasks (Phase 4 & 6)
        if not self.morning_checkin.is_running():
            self.morning_checkin.start()
        if not self.nightly_summary.is_running():
            self.nightly_summary.start()
        if not self.pre_meal_reminder.is_running():
            self.pre_meal_reminder.start()

    @tasks.loop(time=time(8, 0, tzinfo=pu.LOCAL_TZ))
    async def morning_checkin(self):
        """Proactive morning check-in (Phase 4)."""
        logger.info("🌤️ Running scheduled morning health check-ins...")
        
        # In a real production bot, we would iterate over all active users in Supabase.
        # For this implementation, we'll process the cached users who have opted in.
        for user_id in list(pu._user_profiles_cache.keys()):
            profile = pu._user_profiles_cache[user_id]
            
            # Generate personalized greeting
            result = await self.engagement_agent.generate_morning_greeting(profile)
            
            embed = discord.Embed(
                title=f"☀️ Good Morning, {profile.get('name', 'there')}!",
                description=result.get("greeting", "Ready for a healthy day?"),
                color=discord.Color.gold()
            )
            embed.add_field(name="🎯 Today's Focus", value=result.get("focus_goal", profile.get("goal")), inline=False)
            embed.add_field(name="💡 Butler Tip", value=result.get("tip", "Remember to stay hydrated!"), inline=False)
            embed.set_footer(text="Settings: Use /settings to manage notifications")
            
            await self._send_proactive_message(user_id, embed)

    @tasks.loop(time=time(21, 30, tzinfo=pu.LOCAL_TZ))
    async def nightly_summary(self):
        """Proactive nightly summary (Phase 4)."""
        logger.info("🌙 Running scheduled nightly health summaries...")
        
        for user_id in list(pu._user_profiles_cache.keys()):
            # 1. Aggregate today's data (Meals + Workouts)
            if pu.profile_db:
                aggregation = pu.profile_db.get_daily_aggregation(user_id)
                profile = pu.get_user_profile(user_id)
                
                # 2. Generate AI Insight
                report = await self.engagement_agent.generate_daily_report(aggregation, profile)
                
                embed = discord.Embed(
                    title="📊 Daily Health Report",
                    description=report.get("summary_text", "Here is your summary for today."),
                    color=discord.Color.purple() if report.get("status") == "on_track" else discord.Color.orange()
                )
                
                embed.add_field(name="🍽️ Intake", value=f"{aggregation['calories_in']:.0f} kcal", inline=True)
                embed.add_field(name="🏋️ Burned", value=f"{aggregation['calories_out']:.0f} kcal", inline=True)
                embed.add_field(name="⚖️ Net", value=f"{aggregation['net_calories']:.0f} kcal", inline=True)
                embed.add_field(name="🚀 Tomorrow", value=report.get("tomorrow_tip", "Keep up the momentum!"), inline=False)
                
                await self._send_proactive_message(user_id, embed)

    @tasks.loop(time=[time(11, 30, tzinfo=pu.LOCAL_TZ), time(17, 30, tzinfo=pu.LOCAL_TZ)])
    async def pre_meal_reminder(self):
        """Active inspiration for upcoming meals (Phase 6)."""
        logger.info("🎰 Running scheduled pre-meal inspiration checks...")
        for user_id in list(pu._user_profiles_cache.keys()):
            try:
                profile = pu.get_user_profile(user_id)
                stats = pu.profile_db.get_today_stats(user_id) if pu.profile_db else {"total_calories": 0}
                target = pu.calculate_daily_target(profile)
                remaining = {"calories": max(0, target - stats["total_calories"])}
                
                embed = discord.Embed(
                    title="🥗 Time for a boost?",
                    description=(
                        f"Hi **{profile.get('name', 'there')}**! It's almost meal time.\n"
                        f"You have **{int(remaining['calories'])} kcal** remaining in your daily budget.\n\n"
                        "Need some healthy inspiration? Try the **Food Roulette** below!"
                    ),
                    color=discord.Color.green()
                )
                view = MealInspirationView(user_id, remaining)
                await self._send_proactive_message(user_id, embed, view=view)
            except Exception as e:
                logger.error(f"Error in pre_meal_reminder for {user_id}: {e}")

    @morning_checkin.before_loop
    @nightly_summary.before_loop
    @pre_meal_reminder.before_loop
    async def before_loops(self):
        await self.wait_until_ready()

    def _persist_chat_message(self, user_id: str, role: str, content: str) -> None:
        """Persist chat message to Supabase with safe type normalization."""
        if not pu.profile_db:
            return

        try:
            normalized_role = str(role or "user")
            normalized_content = str(content or "")
            pu.profile_db.save_message(
                discord_user_id=str(user_id),
                role=normalized_role,
                content=normalized_content,
            )
        except Exception as exc:
            logger.warning(f"Failed to persist chat message: {exc}")

    async def on_message(self, message: discord.Message):
        logger.info(f"📩 Message received: '{message.content}' from {message.author} (ID: {message.author.id}) in {message.guild}/{message.channel}")
        if message.author.bot: return

        # Optional allowlists for demo safety (empty allowlist => allow all)
        if self.allowed_user_ids and message.author.id not in self.allowed_user_ids:
            return
        if self.allowed_channel_ids and message.channel.id not in self.allowed_channel_ids:
            return

        self._persist_chat_message(str(message.author.id), "user", message.content)

        # Helper for user_id and content stripping
        author_id = str(message.author.id)
        
        # Strip mentions to allow @Butler hi or just hi
        clean_content = message.content.replace(f"<@!{self.user.id}>", "").replace(f"<@{self.user.id}>", "").strip()
        content_lower = clean_content.lower()

        # Temporary Connectivity Debug
        if content_lower == "ping":
            logger.info(f"🏓 Ping matching for {message.author}")
            await message.reply("🏓 pong! I am alive and can see your messages.")
            return

        # /reset Command: Clear user profile and cache
        if content_lower == "/reset":
            await cmd.handle_reset_command(message, HealthButlerEmbed, OnboardingGreetingView)
            return

        # Phase 6.1/6.2: Premium "Cold Start" Onboarding Hook
        greetings = ["hi", "hello", "你好", "start", "hey", "👋"]
        if content_lower in greetings or content_lower == "/setup":
            logger.info(f"👋 Greeting detected from {message.author}: {content_lower}")
            profile = pu.get_user_profile(author_id)
            onboarding_done = profile.get("preferences", {}).get("onboarding_completed", False)
            if not onboarding_done and "preferences_json" in profile:
                onboarding_done = profile.get("preferences_json", {}).get("onboarding_completed", False)

            # /setup always triggers it, 'hi' only for new users
            if not onboarding_done or content_lower == "/setup":
                greeting_text = f"Hi **{message.author.display_name}**! I'm **Health Butler**. Let's set up your profile for safety-first health advice."
                
                # Wrapped callback for modal
                async def on_submit_wrapper(interaction, data):
                    await cmd._on_registration_modal_submit(interaction, data, HealthButlerEmbed)

                view = OnboardingGreetingView(
                    on_registration_submit=on_submit_wrapper, 
                    embed_factory=HealthButlerEmbed
                )
                await message.reply(greeting_text, view=view)
                return

        if message.content.strip().lower().startswith("/demo"):
            await cmd.handle_demo_command(message)
            return

        if message.content.strip().lower() == "/exit":
            await cmd.handle_exit_command(message)
            return

        if message.content.strip().lower() == "/settings":
            await cmd.handle_settings_command(message)
            return

        if message.content.strip().lower() == "/help":
            await cmd.handle_help_command(message, HealthButlerEmbed)
            return

        # Phase 8: Sensitive Query Redirection
        # Redirect Summary, Trends, and Profile queries to DM if in a public channel.
        is_public = message.guild is not None
        # Exceptions for private threads
        if isinstance(message.channel, discord.Thread) and message.channel.type == discord.ChannelType.private_thread:
            is_public = False
            
        if is_public and ip._is_sensitive_query(content_lower):
            logger.info(f"🔒 Redirecting sensitive query to DM for {message.author}")
            
            # 1. Notify in public channel
            privacy_msg = f"🔒 **Privacy Protection**: Hi {message.author.mention}, I've sent your requested health data to our **Direct Messages** to keep it peronal! 📬"
            await message.reply(privacy_msg)
            
            # 2. Re-route the response logic but send to DM
            # We'll mock a DM message object to reuse existing logic
            dm_channel = await message.author.create_dm()
            
            # Trends Redirection
            if "/trends" in content_lower or "trend" in content_lower:
                await dm_channel.send("🔍 Analyzing your health trends... (Redirected from public channel)")
                # ... existing trends logic ...
                profile = pu.get_user_profile(author_id)
                historical_data = pu.profile_db.get_monthly_trends_raw(author_id) if pu.profile_db else []
                analysis = await self.analytics_agent.analyze_trends(historical_data, profile)
                embed = HealthButlerEmbed.build_trends_embed(profile.get("name", "User"), analysis, historical_data)
                await dm_channel.send(embed=embed)
                return

            # Summary Redirection
            if ip._is_daily_summary_query(content_lower):
                await self._send_daily_summary_embed(dm_channel, author_id)
                return

            # Profile Redirection
            if ip._is_profile_query(content_lower):
                await self._send_user_profile_embed(dm_channel, author_id, pu.get_user_profile(author_id))
                return

        if message.content.strip().lower() == "/trends":
            profile = get_user_profile(author_id)
            if not profile or not profile.get("name"):
                await message.channel.send("⚠️ You need to complete your profile first! Use `/setup` or type anything health-related.")
                return

            await message.channel.send("🔍 Analyzing your health trends... this may take a moment.")
            
            if profile_db:
                # 1. Fetch monthly stats from optimized view (v6.0)
                historical_data = profile_db.get_monthly_trends_raw(author_id)
                # Fallback if view is empty but daily_logs might have data
                if not historical_data:
                    historical_data = profile_db.get_historical_trends(author_id, days=30)
                
                # 2. Process with AnalyticsAgent
                analysis = await self.analytics_agent.analyze_trends(historical_data, profile)
                
                # 3. Build & Send Embed
                embed = HealthButlerEmbed.build_trends_embed(
                    user_name=profile.get("name", "User"),
                    trend_data=analysis,
                    historical_raw=historical_data
                )
                await message.channel.send(embed=embed)
            else:
                await message.channel.send("⚠️ Database not available for trend analysis.")
            return

        if message.content.strip().lower() == "/roulette":
            profile = get_user_profile(author_id)
            if not profile or not profile.get("name"):
                await message.channel.send("⚠️ You need to complete your profile first! Use `/setup` or type anything health-related.")
                return
                
            stats = profile_db.get_today_stats(author_id) if profile_db else {"total_calories": 0}
            target = pu.calculate_daily_target(profile)
            remaining = {"calories": max(0, target - stats["total_calories"])}
            
            embed = discord.Embed(
                title="🎰 Food Roulette",
                description=(
                    f"Hi **{profile.get('name', 'there')}**! Need some healthy inspiration?\n"
                    f"You have **{int(remaining['calories'])} kcal** remaining today.\n\n"
                    "Click below to spin the wheel for a personalized meal idea!"
                ),
                color=discord.Color.green()
            )
            from src.discord_bot.roulette_view import MealInspirationView
            view = MealInspirationView(author_id, remaining)
            await message.channel.send(embed=embed, view=view)
            return

        if message.content.strip().lower().startswith("!settings"):
            await self._handle_settings_command(message)
            return

        if message.content.strip().lower() in ("/exit", "/quit"):
            if pu.demo_mode: await cmd.handle_exit_command(message)
            else: await message.channel.send("⚠️ Use `/demo` first.")
            return

        if pu.demo_mode and str(message.author.id) != pu.demo_user_id: return

        # Load profile (prefer in-memory demo profile, fallback to persisted profile)
        profile = pu.get_user_profile(str(message.author.id))
        
        # 1. Profile Queries (Who am I?)
        if ip._is_profile_query(content_lower):
            await self._send_user_profile_embed(message.channel, author_id, profile)
            return

        # 2. Daily Summary Queries (Today's summary)
        if ip._is_daily_summary_query(content_lower):
            await self._send_daily_summary_embed(message.channel, author_id)
            return

        # 3. Help Queries
        if ip._is_help_query(content_lower):
            await cmd.handle_help_command(message, HealthButlerEmbed)
            return

        try:
            image_attachment = next((a for a in message.attachments if a.content_type and a.content_type.startswith('image/')), None)
            user_context = {
                "user_id": str(message.author.id),
                "username": message.author.display_name,
                "name": profile.get("name", message.author.display_name),
                "age": profile.get("age", 30),
                "gender": profile.get("gender", "Not specified"),
                "height": profile.get("height", profile.get("height_cm", 170)),
                "weight": profile.get("weight", profile.get("weight_kg", 70)),
                "conditions": profile.get("conditions", []),
                "goal": profile.get("goal", "General Health"),
                "activity": profile.get("activity", "Moderately Active"),
                "diet": profile.get("diet", []),
                "preferences": profile.get("preferences", {}),
                "daily_intake": profile.get("meals", [])
            }

            async with message.channel.typing():
                if image_attachment:
                    image_path = f"/tmp/{image_attachment.filename}"
                    await image_attachment.save(image_path)
                    
                    # Iterative status message for streaming feedback
                    status_msg = await message.channel.send("📸 *Image received, analyzing components...*")
                    
                    async def progress_update(state: str, status_text: str):
                        try:
                            await status_msg.edit(content=status_text)
                        except Exception:
                            pass

                    try:
                        result = await self.swarm.execute_async(
                            user_input="Analyze this meal", 
                            image_path=image_path, 
                            user_context=user_context,
                            progress_callback=progress_update
                        )
                    finally:
                        if os.path.exists(image_path):
                            os.remove(image_path)
                        try:
                            await status_msg.delete()
                        except Exception:
                            pass
                else:
                    result = await self.swarm.execute_async(
                        user_input=message.content, 
                        user_context=user_context
                    )

                # Persist scanned meals only (image uploads). Text-only nutrition queries should NOT
                # auto-affect consumed totals.
                latest_meal = None
                if image_attachment:
                    try:
                        parsed = self._extract_json_payload(result.get("response") or "")
                        macros = (parsed or {}).get("total_macros", {}) if isinstance(parsed, dict) else {}
                        calories = self._to_float(macros.get("calories", 0), 0.0)
                        confidence = self._to_float(
                            (parsed or {}).get("confidence_score", (parsed or {}).get("total_confidence", 0.0)),
                            0.0,
                        )
                        # Avoid logging "no food detected" / 0-kcal scans automatically.
                        if calories > 0 and confidence >= 0.10:
                            latest_meal = await self._persist_meal_data(result["response"], str(message.author.id))
                    except Exception:
                        latest_meal = None

                await self._send_swarmed_response(
                    message.channel,
                    result["response"],
                    str(message.author.id),
                    latest_meal=latest_meal,
                    scan_mode=bool(image_attachment),
                )

        except Exception as e:
            logger.error(f"Error: {e}")
            await message.channel.send(f"⚠️ Error: {str(e)}")

    async def _send_swarmed_response(
        self,
        channel,
        response: str,
        interaction_user_id: str,
        latest_meal: Optional[Dict[str, Any]] = None,
        *,
        scan_mode: bool = False,
    ):
        try:
            clean_str = response.strip()
            self._persist_chat_message(str(interaction_user_id), "assistant", clean_str)
            data = self._extract_json_payload(clean_str)

            # If we have structured data, use the Unified Embed Design
            if isinstance(data, dict):
                # Check if it's a Nutrition analysis
                if "dish_name" in data and "total_macros" in data:
                    embed = self._build_nutrition_embed(data)
                    view = None
                    if scan_mode:
                        view = MealLogView(
                            self,
                            user_id=str(interaction_user_id),
                            nutrition_payload=data,
                            logged_meal=latest_meal,
                        )
                        # Add a visible status marker at send-time (so user doesn't need to click).
                        if latest_meal and latest_meal.get("meal_id"):
                            embed.title = "✅ " + (embed.title or "Nutrition Analysis")
                        else:
                            embed.title = "📝 " + (embed.title or "Nutrition Analysis")
                            if embed.footer and embed.footer.text:
                                embed.set_footer(text=embed.footer.text + " • Not logged yet")
                            else:
                                embed.set_footer(text="Not logged yet")

                    if view:
                        await channel.send(embed=embed, view=view)
                    else:
                        await channel.send(embed=embed)
                elif "summary" in data and ("recommendations" in data or "exercises" in data):
                    user_profile = pu.get_user_profile(str(interaction_user_id))
                    display_name = user_profile.get("name") or "User"
                    embed = self._build_fitness_embed(data, user_name=display_name)
                    await self._persist_fitness_plan(data, interaction_user_id)
                    await channel.send(embed=embed, view=LogWorkoutView(self, data, interaction_user_id))
                else:
                    # Fallback for other specialist agents or generic JSON
                    embed = Embed(title="💎 Health Butler Analysis", color=discord.Color.blue())
                    for k, v in data.items():
                        if isinstance(v, (str, int, float)) and len(str(v)) < 1000:
                            embed.add_field(name=k.replace("_", " ").title(), value=str(v), inline=False)
                    await channel.send(embed=embed)
                
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

    async def _send_user_profile_embed(self, channel, user_id: str, profile: Dict[str, Any]) -> None:
        """Send a profile summary embed (no agent routing)."""
        # Basic existence check
        has_any = any(
            profile.get(k)
            for k in (
                "name",
                "age",
                "gender",
                "height",
                "height_cm",
                "weight",
                "weight_kg",
                "goal",
                "activity",
                "diet",
                "conditions",
                "preferences",
            )
        )
        if not has_any or profile == {"meals": []}:
            await channel.send("⚠️ I don't have a saved profile for you yet. Run `/demo` to register.")
            return

        name = profile.get("name") or "Not provided"
        age = profile.get("age", "N/A")
        gender = profile.get("gender", "N/A")
        height = profile.get("height", profile.get("height_cm", "N/A"))
        weight = profile.get("weight", profile.get("weight_kg", "N/A"))
        goal = profile.get("goal", "General Health")
        activity = profile.get("activity", "Moderately Active")
        diet = profile.get("diet", [])
        conditions = profile.get("conditions", [])
        prefs = profile.get("preferences", {}) if isinstance(profile.get("preferences"), dict) else {}

        # Determine persistence status
        saved = False
        try:
            if pu.profile_db and pu.profile_db.get_profile(str(user_id)):
                saved = True
        except Exception:
            saved = False

        embed = Embed(title="👤 Your Profile", color=discord.Color.blurple())
        embed.add_field(name="Name", value=str(name), inline=True)
        embed.add_field(name="Age / Gender", value=f"{age} / {gender}", inline=True)
        embed.add_field(name="Metrics", value=f"{height} cm / {weight} kg", inline=False)
        embed.add_field(name="Goal", value=str(goal), inline=True)
        embed.add_field(name="Activity", value=str(activity), inline=True)
        embed.add_field(
            name="Conditions",
            value=", ".join(conditions) if conditions else "None",
            inline=False,
        )
        embed.add_field(
            name="Diet",
            value=", ".join(diet) if isinstance(diet, list) and diet else "None",
            inline=False,
        )
        if prefs:
            pref_lines = []
            if "sleep_hours" in prefs:
                pref_lines.append(f"Sleep: {prefs.get('sleep_hours')}h")
            if "stress_level" in prefs:
                pref_lines.append(f"Stress: {prefs.get('stress_level')}/10")
            if "workout_days_per_week" in prefs:
                pref_lines.append(f"Workout days: {prefs.get('workout_days_per_week')}/wk")
            if "session_minutes" in prefs:
                pref_lines.append(f"Session: {prefs.get('session_minutes')} min")
            if "motivation_style" in prefs:
                pref_lines.append(f"Motivation: {prefs.get('motivation_style')}")
            if pref_lines:
                embed.add_field(name="Personalization", value=" | ".join(pref_lines), inline=False)

        embed.set_footer(
            text="✅ Saved to database" if saved else "⚠️ In-session only (Supabase not configured)"
        )
        await channel.send(embed=embed)

    def _extract_json_payload(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract the most relevant JSON object from model output text.

        Priority:
        1) Whole-string JSON object
        2) Any embedded JSON object containing nutrition payload keys
        3) First embedded JSON object
        """
        if not text:
            return None

        clean = text.strip()

        if "```json" in clean:
            clean = clean.split("```json")[-1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[-1].split("```")[0].strip()

        try:
            payload = json.loads(clean)
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass

        decoder = JSONDecoder()
        candidates: List[Dict[str, Any]] = []
        for idx, ch in enumerate(clean):
            if ch != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(clean, idx)
                if isinstance(obj, dict):
                    candidates.append(obj)
            except Exception:
                continue

        if not candidates:
            return None

        preferred = next(
            (
                obj
                for obj in candidates
                if "dish_name" in obj and "total_macros" in obj
            ),
            None,
        )
        if preferred:
            return preferred

        return candidates[0]

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _macros_from_items(self, data: Dict[str, Any]) -> Dict[str, float]:
        totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        for item in data.get("items_detected", []) or []:
            if not isinstance(item, dict):
                continue
            macros = item.get("macros", {})
            for key in totals:
                totals[key] += self._to_float(macros.get(key, 0), 0.0)
        return totals

    def _calorie_breakdown_rows(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return normalized calorie breakdown rows for embed display."""
        normalized_rows: List[Dict[str, Any]] = []

        def aggregate_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            grouped: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                item_name = str(row.get("item") or "Unknown").strip()
                qty = max(1, int(self._to_float(row.get("quantity"), 1)))
                c_total = self._to_float(row.get("calories_total"), 0.0)
                if c_total <= 0:
                    continue

                if item_name not in grouped:
                    grouped[item_name] = {
                        "item": item_name,
                        "quantity": 0,
                        "calories_total": 0.0,
                    }
                grouped[item_name]["quantity"] += qty
                grouped[item_name]["calories_total"] += c_total

            output: List[Dict[str, Any]] = []
            for row in grouped.values():
                quantity = row["quantity"]
                calories_total = round(row["calories_total"], 1)
                output.append(
                    {
                        "item": row["item"],
                        "quantity": quantity,
                        "calories_each": round(calories_total / quantity, 1),
                        "calories_total": calories_total,
                    }
                )

            return output

        source_rows = data.get("calorie_breakdown", []) or []
        for row in source_rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("item") or "Unknown").strip()
            quantity = max(1, int(self._to_float(row.get("quantity"), 1)))
            c_each = round(self._to_float(row.get("calories_each"), 0.0), 1)
            c_total = round(self._to_float(row.get("calories_total"), 0.0), 1)
            if c_total <= 0:
                continue
            normalized_rows.append(
                {
                    "item": name,
                    "quantity": quantity,
                    "calories_each": c_each if c_each > 0 else round(c_total / quantity, 1),
                    "calories_total": c_total,
                }
            )

        if normalized_rows:
            return aggregate_rows(normalized_rows)

        for item in data.get("items_detected", []) or []:
            if not isinstance(item, dict):
                continue
            macros = item.get("macros", {}) or {}
            item_total = round(self._to_float(macros.get("calories"), 0.0), 1)
            if item_total <= 0:
                continue
            normalized_rows.append(
                {
                    "item": str(item.get("name") or "Unknown"),
                    "quantity": 1,
                    "calories_each": item_total,
                    "calories_total": item_total,
                }
            )

        return aggregate_rows(normalized_rows)

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

        cals = self._to_float(macros.get("calories", 0), 0.0)
        p = self._to_float(macros.get("protein", 0), 0.0)
        c = self._to_float(macros.get("carbs", 0), 0.0)
        f = self._to_float(macros.get("fat", 0), 0.0)

        if cals <= 0 and p <= 0 and c <= 0 and f <= 0:
            recovered = self._macros_from_items(data)
            if recovered["calories"] > 0:
                cals, p, c, f = recovered["calories"], recovered["protein"], recovered["carbs"], recovered["fat"]
                data["total_macros"] = {"calories": round(cals, 1), "protein": round(p, 1), "carbs": round(c, 1), "fat": round(f, 1)}

        breakdown_rows = self._calorie_breakdown_rows(data)
        if breakdown_rows and cals <= 0:
            cals = round(sum(row.get("calories_total", 0.0) for row in breakdown_rows), 1)
            data.setdefault("total_macros", {})["calories"] = cals
        
        embed.description = f"🔥 **{cals}** kcal | 🍖 **{p}g** P | 🍞 **{c}g** C | 🥑 **{f}g** F"

        total_g = p + c + f
        if total_g > 0:
            def get_bar(val):
                pct = int((val / total_g) * 20)
                return "█" * pct + "░" * (20 - pct)

            def color_bar(val, marker: str):
                pct = int((val / total_g) * 12)
                return marker * pct + "⬛" * (12 - pct)
            
            p_pct = (p / total_g) * 100
            c_pct = (c / total_g) * 100
            f_pct = (f / total_g) * 100
            
            breakdown = (
                f"🍖 **Protein** {p_pct:2.0f}% • {round(p, 1)}g\n"
                f"{color_bar(p, '🟦')}\n"
                f"🍞 **Carbs** {c_pct:2.0f}% • {round(c, 1)}g\n"
                f"{color_bar(c, '🟨')}\n"
                f"🥑 **Fat** {f_pct:2.0f}% • {round(f, 1)}g\n"
                f"{color_bar(f, '🟩')}"
            )
            embed.add_field(name="📊 Macros Breakdown", value=breakdown, inline=False)

        # Phase 6: Daily Impact & Remaining Budget
        dv = data.get("daily_value_percentage", {})
        budget = data.get("remaining_budget", {})
        if dv or budget:
            def render_impact_line(label, current_pct, remaining_val, unit="", marker="🟧"):
                filled = int(min(100, current_pct) / 10)
                bar = marker * filled + "⬜" * (10 - filled)
                return f"**{label}**: `{bar}` **{current_pct:.1f}%**\n➡️ *Remaining: {remaining_val} {unit}*"

            impact_text = (
                render_impact_line("Calories", dv.get("calories", 0), budget.get("calories", 0), "kcal", "🟧") + "\n" +
                render_impact_line("Protein", dv.get("protein", 0), budget.get("protein", 0), "g", "🟦") + "\n" +
                render_impact_line("Carbs", dv.get("carbs", 0), budget.get("carbs", 0), "g", "🟨") + "\n" +
                render_impact_line("Fat", dv.get("fat", 0), budget.get("fat", 0), "g", "🟩")
            )
            embed.add_field(name="📈 Daily Impact & Remaining Budget", value=impact_text, inline=False)

        if breakdown_rows:
            detail_lines = []
            for row in breakdown_rows[:6]:
                qty = row.get("quantity", 1)
                line = (
                    f"• {row.get('item', 'Item')}: {row.get('calories_each', 0):.1f} kcal"
                    f" × {qty} = **{row.get('calories_total', 0):.1f} kcal**"
                )
                detail_lines.append(line)

            listed_total = sum(self._to_float(row.get("calories_total"), 0.0) for row in breakdown_rows)
            detail_lines.append(f"**Overall Total: {listed_total:.1f} kcal**")
            embed.add_field(name="🍽️ Calories by Item", value="\n".join(detail_lines), inline=False)

        ingredients = data.get("ingredients_with_portions", [])
        if not ingredients:
            raw_items = data.get("items_detected", [])
            normalized = []
            for item in raw_items[:6]:
                if isinstance(item, dict):
                    name = item.get("name", "Unknown")
                    portion = item.get("estimated_weight_grams")
                    if portion:
                        normalized.append(f"{name} (~{portion}g)")
                    else:
                        normalized.append(name)
                else:
                    normalized.append(str(item))
            ingredients = normalized

        ing_list = "\n".join([f"• {i}" for i in ingredients[:6]]) if ingredients else "Not specified"
        embed.add_field(name="🥗 Key Ingredients", value=ing_list, inline=False)

        insight = self._compose_health_insight(data, cals)
        embed.add_field(name="💡 Health Insight", value=insight, inline=False)

        embed.set_footer(text=f"Confidence: {stars} ({int(confidence*100)}%) • Anchored to USDA data + visual estimation")
        return embed

    def _compose_health_insight(self, data: Dict[str, Any], calories: float) -> str:
        """Generate a concise 1-3 sentence overview (food + workout + status)."""
        base_tip = data.get("health_tip") or data.get("composition_analysis") or "Meal analyzed successfully."

        if calories >= 700:
            workout_sentence = "Workout suggestion: add 35-45 minutes of moderate cardio or a brisk walk."
            status_sentence = f"Food and current status: this meal is about {int(calories)} kcal and is on the higher side, so keep your next meal lighter and protein-focused."
        elif calories >= 350:
            workout_sentence = "Workout suggestion: 20-30 minutes of activity helps keep daily balance."
            status_sentence = f"Food and current status: this meal is about {int(calories)} kcal and fits a moderate intake range for most goals."
        else:
            workout_sentence = "Workout suggestion: a short 10-20 minute walk is enough for digestion and consistency."
            status_sentence = f"Food and current status: this meal is about {int(calories)} kcal and is relatively light, leaving flexibility for later meals."

        concise_base = base_tip.split(".")[0].strip()
        tip_line = f"• {concise_base}." if concise_base else "• Meal analyzed successfully."
        status_line = f"• {status_sentence}"
        workout_line = f"• {workout_sentence}"
        return "\n".join([tip_line, status_line, workout_line])

    def _build_fitness_embed(self, data: Dict[str, Any], user_name: str = "User") -> Embed:
        """Build fitness-specific embed for structured FitnessAgent output using HealthButlerEmbed factory."""
        return HealthButlerEmbed.build_fitness_card(data, user_name=user_name)

    async def _persist_fitness_plan(self, data: Dict[str, Any], user_id: str) -> None:
        """Persist recommended workouts so plans are tracked in Supabase."""
        if not pu.profile_db:
            return
        try:
            for rec in (data.get("recommendations", []) or [])[:5]:
                pu.profile_db.log_workout_event(
                    discord_user_id=user_id,
                    exercise_name=str(rec.get("name", "Exercise")),
                    duration_min=int(self._to_float(rec.get("duration_min", 20), 20)),
                    kcal_estimate=self._to_float(rec.get("kcal_estimate", 80), 80),
                    status="recommended",
                    source="fitness_agent",
                    raw_payload=rec,
                )
        except Exception as e:
            logger.warning(f"Failed to persist fitness plan: {e}")

    async def _send_daily_summary_embed(self, channel, user_id: str, latest_meal: Optional[Dict[str, Any]] = None):
        """Send a 'Today's Summary' embed as requested by user."""
        if not user_id:
            return

        # Demo mode: compute totals from in-memory meal log (no DB dependency).
        if pu.demo_mode and pu.demo_user_id and str(user_id) == str(pu.demo_user_id):
            try:
                profile = pu._demo_user_profile.get(str(user_id)) or pu.get_user_profile(str(user_id)) or {"meals": []}
                meals = profile.get("meals", []) or []
                consumed = sum(float((m.get("macros") or {}).get("calories", 0) or 0) for m in meals)
                meals_count = len(meals)
                target = pu.calculate_daily_target(profile)

                percent = (consumed / target * 100) if target > 0 else 0
                remaining = target - consumed

                embed = Embed(title="🟢 Today's Summary", color=discord.Color.green())
                embed.add_field(
                    name="📊 Calories",
                    value=f"**{consumed}** / {target} kcal ({percent:.1f}%)",
                    inline=False,
                )
                embed.add_field(name="🍽️ Meals", value=f"**{meals_count}**", inline=True)
                if remaining > 0:
                    embed.add_field(name="💡 Status", value=f"You can have about **{remaining}** more kcal", inline=False)
                else:
                    embed.add_field(name="⚠️ Status", value=f"Over target by **{abs(remaining)}** kcal", inline=False)
                await channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Failed to send daily summary (demo): {e}")
            return

        if not pu.profile_db:
            return
        
        try:
            profile = pu.get_user_profile(user_id)
            stats = pu.profile_db.get_today_stats(user_id)
            target = pu.calculate_daily_target(profile)
            
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
            data = self._extract_json_payload(response)
            if not data:
                return None

            if "dish_name" in data and "total_macros" in data:
                m = data["total_macros"]
                meal_record = {
                    "meal_id": None,
                    "time": datetime.now(LOCAL_TZ).strftime("%H:%M"),
                    "dish": data["dish_name"],
                    "macros": data["total_macros"]
                }

                # Demo mode: in-memory only
                if pu.demo_mode and user_id == pu.demo_user_id:
                    if user_id not in pu._demo_user_profile:
                        pu._demo_user_profile[user_id] = {"meals": []}
                    meal_record["meal_id"] = f"demo-{uuid.uuid4().hex[:10]}"
                    pu._demo_user_profile[user_id].setdefault("meals", []).append(meal_record)
                    logger.info(f"📝 Demo meal saved: {data['dish_name']}")

                # Real user: persist to Supabase
                elif pu.profile_db:
                    from datetime import date
                    today = date.today()
                    calories = float(m.get('calories', 0) or 0)
                    protein = float(m.get('protein', 0) or 0)
                    carbs = float(m.get('carbs', 0) or 0)
                    fat = float(m.get('fat', 0) or 0)

                    # Keep legacy daily_logs write for backwards compatibility (tests + older schema).
                    try:
                        pu.profile_db.create_daily_log(
                            discord_user_id=user_id,
                            log_date=today,
                            calories_intake=calories,
                            protein_g=protein,
                        )
                    except Exception:
                        pass

                    # 1. Create detailed meal record (source of truth for totals)
                    created = pu.profile_db.create_meal(
                        discord_user_id=user_id,
                        dish_name=data["dish_name"],
                        calories=calories,
                        protein_g=protein,
                        carbs_g=carbs,
                        fat_g=fat,
                        confidence_score=data.get("confidence_score") or data.get("total_confidence", 0.0)
                    )
                    meal_record["meal_id"] = (created or {}).get("id")
                    logger.info(f"💾 Detailed meal persisted to DB: {data['dish_name']} ({calories} kcal)")

                    # 2. Recompute daily log totals from meals (keeps daily_logs consistent)
                    try:
                        pu.profile_db.recompute_daily_log_from_meals(user_id, today)
                    except Exception:
                        pass

                    # Also update local cache
                    if user_id in pu._user_profiles_cache:
                        pu._user_profiles_cache[author_id].setdefault("meals", []).append(meal_record)

                return meal_record

        except Exception as e:
            logger.debug(f"Meal persist error: {e}")

        return None

# Command methods removed, logic moved to cmd module.

def main():
    bot = HealthButlerDiscordBot()
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        logger.error("No DISCORD_TOKEN found.")

if __name__ == "__main__":
    main()
