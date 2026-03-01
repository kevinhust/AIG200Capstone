import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING
import discord
from discord import Embed, Interaction, ui
from src.discord_bot.embed_builder import HealthButlerEmbed
from src.discord_bot import profile_utils as pu
from src.discord_bot.modals import RegistrationModal

if TYPE_CHECKING:
    from src.discord_bot.bot import HealthButlerDiscordBot

logger = logging.getLogger(__name__)

def _apply_serving_multiplier(nutrition_payload: Dict[str, Any], multiplier: float, dish_override: Optional[str] = None) -> Dict[str, Any]:
    """Scale a nutrition payload in-place (and return it) by a serving multiplier."""
    try:
        m = float(multiplier or 1.0)
    except Exception:
        m = 1.0
    if m <= 0:
        m = 1.0

    try:
        prev = float(nutrition_payload.get("serving_multiplier", 1.0) or 1.0)
    except Exception:
        prev = 1.0
    if prev <= 0:
        prev = 1.0

    ratio = m / prev

    if dish_override:
        nutrition_payload["dish_name"] = str(dish_override).strip() or nutrition_payload.get("dish_name")

    macros = nutrition_payload.get("total_macros", {}) or {}
    if isinstance(macros, dict):
        for key in ("calories", "protein", "carbs", "fat"):
            try:
                macros[key] = round(float(macros.get(key, 0) or 0) * ratio, 1)
            except Exception:
                continue
        nutrition_payload["total_macros"] = macros

    rows = nutrition_payload.get("calorie_breakdown", []) or []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            for k in ("calories_each", "calories_total"):
                try:
                    row[k] = round(float(row.get(k, 0) or 0) * ratio, 1)
                except Exception:
                    continue

    nutrition_payload["serving_multiplier"] = round(m, 3)
    return nutrition_payload

class OnboardingGreetingView(ui.View):
    """
    Minimal Greeting View (Phase 6.2).
    Simple 'Hi' + 'Start Setup' button to restore a clean first interaction.
    """
    def __init__(self, on_registration_submit: Any, embed_factory: Any):
        super().__init__(timeout=None)
        self.on_registration_submit = on_registration_submit
        self.embed_factory = embed_factory

    @ui.button(label='Start Setup', style=discord.ButtonStyle.green, emoji='🚀')
    async def enter_onboarding(self, interaction: discord.Interaction, button: ui.Button):
        # Reveal the full Premium Welcome Embed
        from src.discord_bot.views import OnboardingStartView
        embed = self.embed_factory.build_welcome_embed(interaction.user.display_name)
        view = OnboardingStartView(
            on_registration_submit=self.on_registration_submit,
            embed_factory=self.embed_factory
        )
        # Transition from simple text to premium embed
        await interaction.response.edit_message(content=None, embed=embed, view=view)

class StartSetupView(discord.ui.View):
    def __init__(self, on_submit_callback):
        super().__init__(timeout=None)
        self.on_submit_callback = on_submit_callback

    @discord.ui.button(label='Start Setup', style=discord.ButtonStyle.green, emoji='🚀')
    async def start_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegistrationModal(on_submit_callback=self.on_submit_callback))

class OnboardingStartView(ui.View):
    """
    Premium Cold-Start Landing View (Phase 6.1).
    Bridges new users to the onboarding modal or a demo overview.
    """
    def __init__(self, on_registration_submit: Any, embed_factory: Any):
        super().__init__(timeout=None) # No timeout for the main entry point
        self.on_registration_submit = on_registration_submit
        self.embed_factory = embed_factory

    @ui.button(label='Start Onboarding', style=discord.ButtonStyle.green, emoji='🚀')
    async def start_onboarding(self, interaction: discord.Interaction, button: ui.Button):
        # Open Step 1/3 Modal
        await interaction.response.send_modal(RegistrationModal(on_submit_callback=self.on_registration_submit))

    @ui.button(label='View Demo', style=discord.ButtonStyle.blurple, emoji='📖')
    async def view_demo(self, interaction: discord.Interaction, button: ui.Button):
        # Show a pre-canned "Taco Simulation" result to build trust
        await interaction.response.send_message(
            "📝 **Demo Mode**: Here is what Butler does when I analyze a high-calorie meal (like Tacos!) for a user with a knee injury...",
            ephemeral=True
        )
        # Note: In a real bot, we'd send the Taco Embed here. 
        # For simplicity, we can link the user to the documentation or send a summary string.
        demo_text = (
            "✅ Identified: **Assorted Beef Tacos** (1226 kcal)\n"
            "✅ Warning: **High Fat/High Oil** detected.\n"
            "🛡️ **Calorie Balance Shield** triggered! \n"
            "➡️ Butler recommended a *30m Light Walk* and injected safety disclaimer `BR-001`."
        )
        await interaction.followup.send(demo_text, ephemeral=True)

    @ui.button(label='Learn More', style=discord.ButtonStyle.gray, emoji='❓')
    async def learn_more(self, interaction: discord.Interaction, button: ui.Button):
        info_text = (
            "**Personal Health Butler AI v6.1**\n"
            "• **Vision**: YOLO11 Real-time Perception\n"
            "• **Brain**: Health Swarm (Nutrition + Fitness coordination)\n"
            "• **Safety**: RAG-driven medical guardrails\n"
            "• **Persistence**: Supabase v6.0 Cloud Analytics"
        )
        await interaction.response.send_message(info_text, ephemeral=True)

class RegistrationViewA(ui.View):
    """
    Step 2/3: Biological Profile & Goals (v4.1 Mobile Optimized).
    Collects Sex, Goal, and Activity Level to calculate TDEE.
    """
    def __init__(self, user_id: str, profile_buffer: Dict[str, Any], embed_factory):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.profile_buffer = profile_buffer # Reference to _demo_user_profile[user_id]
        self.embed_factory = embed_factory
        
        # Internal state to track selections before showing 'Next'
        self.selected_sex = None
        self.selected_goal = None
        self.selected_activity = None

    @ui.select(
        placeholder="Select Biological Sex (for BMR calculation)...",
        options=[
            discord.SelectOption(label="Male", emoji="👨", value="male"),
            discord.SelectOption(label="Female", emoji="👩", value="female"),
            discord.SelectOption(label="Other / Prefer not to say", emoji="👤", value="other"),
        ],
        custom_id="reg_sex"
    )
    async def select_sex(self, interaction: discord.Interaction, select: ui.Select):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This setup is for someone else!", ephemeral=True)
        
        self.selected_sex = select.values[0]
        await self._update_view_state(interaction)

    @ui.select(
        placeholder="Select Primary Health Goal...",
        options=[
            discord.SelectOption(label="Lose Weight", description="Calorie deficit focus", emoji="📉", value="lose"),
            discord.SelectOption(label="Gain Muscle", description="Calorie surplus/protein focus", emoji="📈", value="gain"),
            discord.SelectOption(label="Maintenance", description="Balanced nutrition focus", emoji="⚖️", value="maintain"),
            discord.SelectOption(label="General Health", description="Overall wellness", emoji="🧘", value="general"),
        ],
        custom_id="reg_goal"
    )
    async def select_goal(self, interaction: discord.Interaction, select: ui.Select):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This setup is for someone else!", ephemeral=True)
        
        self.selected_goal = select.values[0]
        await self._update_view_state(interaction)

    @ui.select(
        placeholder="Select Activity Level...",
        options=[
            discord.SelectOption(label="Sedentary", description="Desk job, little exercise", emoji="🪑", value="sedentary"),
            discord.SelectOption(label="Lightly Active", description="1-3 days/week exercise", emoji="🚶", value="lightly active"),
            discord.SelectOption(label="Moderately Active", description="3-5 days/week exercise", emoji="🏃", value="moderately active"),
            discord.SelectOption(label="Very Active", description="6-7 days/week exercise", emoji="🏋️", value="very active"),
        ],
        custom_id="reg_activity"
    )
    async def select_activity(self, interaction: discord.Interaction, select: ui.Select):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This setup is for someone else!", ephemeral=True)
        
        self.selected_activity = select.values[0]
        await self._update_view_state(interaction)

    async def _update_view_state(self, interaction: discord.Interaction):
        """Check if all selections are made, then show the Next button."""
        if self.selected_sex and self.selected_goal and self.selected_activity:
            # Add the 'Next' button if not already present
            if not any(isinstance(item, ui.Button) and item.label == "Next: Safety & Allergies" for item in self.children):
                next_button = ui.Button(
                    label="Next: Safety & Allergies",
                    style=discord.ButtonStyle.green,
                    emoji="🛡️",
                    custom_id="reg_next_btn"
                )
                next_button.callback = self.on_next_click
                self.add_item(next_button)
        
        # Acknowledge the selection
        await interaction.response.edit_message(view=self)

    async def on_next_click(self, interaction: discord.Interaction):
        """Calculate TDEE and proceed to Step 3."""
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This setup is for someone else!", ephemeral=True)

        try:
            # Update buffer
            self.profile_buffer["gender"] = self.selected_sex
            self.profile_buffer["goal"] = self.selected_goal
            self.profile_buffer["activity"] = self.selected_activity
            
            # Calculate TDEE (Mifflin-St Jeor)
            # Reusing the logic identified in bot.py
            weight = float(self.profile_buffer.get('weight_kg', 70))
            height = float(self.profile_buffer.get('height_cm', 170))
            age = int(self.profile_buffer.get('age', 30))
            
            bmr = (10 * weight) + (6.25 * height) - (5 * age)
            if self.selected_sex == 'female':
                bmr -= 161
            else:
                bmr += 5 # Default to male/other for safety calculation
            
            activity_map = {
                "sedentary": 1.2,
                "lightly active": 1.375,
                "moderately active": 1.55,
                "very active": 1.725
            }
            factor = activity_map.get(self.selected_activity, 1.2)
            tdee = bmr * factor
            
            # Goal adjustment
            if 'lose' in self.selected_goal:
                tdee -= 500
            elif 'gain' in self.selected_goal:
                tdee += 300
                
            self.profile_buffer["tdee"] = int(tdee)
            logger.info(f"Calculated TDEE for {self.user_id}: {int(tdee)} kcal")

            # Transition to Step 3/3
            embed = self.embed_factory.build_progress_embed(
                step=3, 
                total_steps=3,
                title="Safety & Protocols",
                description="Perfect! Last step: Help us understand any health conditions and security preferences to keep you safe."
            )
            
            await interaction.response.edit_message(
                embed=embed,
                view=RegistrationViewB(self.user_id, self.profile_buffer, self.embed_factory)
            )
            await interaction.followup.send(
                f"✅ **Base profile calibrated!** Your target is approximately **{int(tdee)} kcal**/day.",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in RegistrationViewA calculation: {e}")
            await interaction.response.send_message("⚠️ Failed to calibrate profile. Please try again.", ephemeral=True)

class AllergyModal(ui.Modal, title='Manual Allergy Entry'):
    """Optional modal for custom allergy input."""
    other_allergy = ui.TextInput(
        label='Additional Allergies',
        placeholder='e.g. Mango, Kiwi, Peanuts (if not listed)',
        min_length=2,
        max_length=100,
        required=True
    )

    def __init__(self, on_submit_callback):
        super().__init__()
        self.on_submit_callback = on_submit_callback

    async def on_submit(self, interaction: discord.Interaction):
        await self.on_submit_callback(interaction, self.other_allergy.value)

class ConditionModal(ui.Modal, title='Manual Chronic Issue Entry'):
    """Optional modal for custom chronic condition input."""
    other_condition = ui.TextInput(
        label='Chronic Issue (e.g. Asthma, Hernia)',
        placeholder='Note: Tell me about short-term issues in chat!',
        min_length=2,
        max_length=100,
        required=True
    )

    def __init__(self, on_submit_callback):
        super().__init__()
        self.on_submit_callback = on_submit_callback

    async def on_submit(self, interaction: discord.Interaction):
        await self.on_submit_callback(interaction, self.other_condition.value)

class RegistrationViewB(ui.View):
    """
    Step 3/3: Safety & Allergies (v4.1).
    Collects Allergies and Health Conditions, then persists to Supabase.
    """
    def __init__(self, user_id: str, profile_buffer: Dict[str, Any], embed_factory):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.profile_buffer = profile_buffer
        self.embed_factory = embed_factory
        
        self.selected_allergies = []
        self.selected_conditions = []

    @ui.select(
        placeholder="Select Allergies (Multi-select)...",
        min_values=0,
        max_values=8,
        options=[
            discord.SelectOption(label="Nuts", emoji="🥜", value="Nuts"),
            discord.SelectOption(label="Seafood", emoji="🍤", value="Seafood"),
            discord.SelectOption(label="Dairy", emoji="🥛", value="Dairy"),
            discord.SelectOption(label="Gluten", emoji="🌾", value="Gluten"),
            discord.SelectOption(label="Soy", emoji="🫘", value="Soy"),
            discord.SelectOption(label="Eggs", emoji="🥚", value="Eggs"),
            discord.SelectOption(label="Sesame", emoji="🥯", value="Sesame"),
            discord.SelectOption(label="Other (Manual Entry)", emoji="➕", value="Other"),
        ],
        custom_id="reg_allergies"
    )
    async def select_allergies(self, interaction: discord.Interaction, select: ui.Select):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This setup is for someone else!", ephemeral=True)
        self.selected_allergies = select.values
        await interaction.response.edit_message(view=self)

    @ui.select(
        placeholder="Select Chronic Conditions & Injuries...",
        min_values=0,
        max_values=5,
        options=[
            discord.SelectOption(label="No Conditions", emoji="✅", value="None"),
            discord.SelectOption(label="Hypertension", emoji="💓", value="Hypertension"),
            discord.SelectOption(label="Diabetes", emoji="🩸", value="Diabetes"),
            discord.SelectOption(label="Knee Injury / Pain", emoji="🦵", value="Knee Injury"),
            discord.SelectOption(label="Lower Back Pain", emoji="🔙", value="Lower Back Pain"),
            discord.SelectOption(label="Other Chronic Issue (Manual Entry)", emoji="➕", value="Other"),
        ],
        custom_id="reg_conditions"
    )
    async def select_conditions(self, interaction: discord.Interaction, select: ui.Select):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This setup is for someone else!", ephemeral=True)
        self.selected_conditions = select.values
        await interaction.response.edit_message(view=self)

    @ui.button(label="Finish & Activate Butler", style=discord.ButtonStyle.green, emoji="🏁", custom_id="reg_finish_btn")
    async def finish_registration(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This setup is for someone else!", ephemeral=True)

        # Check if "Other" is selected in allergies or conditions
        if "Other" in self.selected_allergies:
            await interaction.response.send_modal(AllergyModal(on_submit_callback=self._handle_manual_allergy))
        elif "Other" in self.selected_conditions:
            await interaction.response.send_modal(ConditionModal(on_submit_callback=self._handle_manual_condition))
        else:
            await self._finalize_persistence(interaction)

    async def _handle_manual_allergy(self, interaction: discord.Interaction, manual_entry: str):
        """Callback from AllergyModal."""
        # Clean up "Other" and add manual entry
        self.selected_allergies = [a for a in self.selected_allergies if a != "Other"]
        if manual_entry:
            self.selected_allergies.append(manual_entry)
            
        # Chain to condition modal if needed
        if "Other" in self.selected_conditions:
            await interaction.response.send_modal(ConditionModal(on_submit_callback=self._handle_manual_condition))
        else:
            await self._finalize_persistence(interaction)

    async def _handle_manual_condition(self, interaction: discord.Interaction, manual_entry: str):
        """Callback from ConditionModal."""
        self.selected_conditions = [c for c in self.selected_conditions if c != "Other"]
        if manual_entry:
            self.selected_conditions.append(manual_entry)
        await self._finalize_persistence(interaction)

    async def _finalize_persistence(self, interaction: discord.Interaction):
        """Final save to database and welcome message."""
        try:
            # Map selected conditions/allergies
            conditions = [c for c in self.selected_conditions if c != "None"]
            
            # Combine everything into profile_buffer
            self.profile_buffer["conditions"] = conditions
            self.profile_buffer["diet"] = self.selected_allergies # Mapping allergies to 'diet' for consistency with schema
            
            # Add onboarding metadata
            prefs = self.profile_buffer.get("preferences_json", {})
            prefs["onboarding_completed"] = True
            prefs["registration_date"] = datetime.now().isoformat()
            self.profile_buffer["preferences_json"] = prefs

            # BMI Calculation: weight / (height/100)^2
            h_m = float(self.profile_buffer["height_cm"]) / 100
            w_kg = float(self.profile_buffer["weight_kg"])
            bmi = w_kg / (h_m * h_m)
            self.profile_buffer["bmi"] = round(bmi, 1)

            # SAVE TO SUPABASE
            from src.discord_bot.profile_db import get_profile_db
            db = get_profile_db()
            
            # Use create_profile for new registrations
            db.create_profile(
                discord_user_id=self.user_id,
                full_name=self.profile_buffer["name"],
                age=int(self.profile_buffer["age"]),
                gender=self.profile_buffer["gender"],
                height_cm=float(self.profile_buffer["height_cm"]),
                weight_kg=float(self.profile_buffer["weight_kg"]),
                goal=self.profile_buffer["goal"],
                conditions=conditions,
                activity=self.profile_buffer["activity"],
                diet=self.selected_allergies,
                preferences=self.profile_buffer["preferences_json"]
            )

            # Build Welcome Embed
            embed = discord.Embed(
                title="✨ Welcome to Health Butler AI v7.0!",
                description=(
                    f"Congratulations **{self.profile_buffer['name']}**! Your personalized health profile is now active.\n\n"
                    f"**Your Stats Summary:**\n"
                    f"• BMI: **{self.profile_buffer['bmi']}**\n"
                    f"• Daily Target: **{self.profile_buffer.get('tdee', 2000)} kcal**\n"
                    f"• Health Goal: **{self.profile_buffer['goal'].title()}**\n"
                    f"• Safety Tags: {', '.join(self.selected_allergies) or 'None'}\n\n"
                    "🔒 **Privacy Tip**: For maximum safety, I suggest we continue our conversation in **Direct Messages (DMs)** or a **Private Thread**. Your health data is your own!"
                ),
                color=discord.Color.gold()
            )
            embed.set_footer(text="🛡️ BR-001: Medical Disclaimer - Not a substitute for professional advice.")
            
            # Standard v3.0 buttons like 'Log Meal' would go in a new View, but for now we finish.
            await interaction.response.edit_message(
                embed=embed,
                view=None
            )
            
            await interaction.followup.send("🚀 **Profile Activated!** You are all set.", ephemeral=True)

        except Exception as e:
            logger.error(f"Persistence error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("⚠️ Error saving profile. Please contact support.", ephemeral=True)
            else:
                await interaction.followup.send("⚠️ Error saving profile. Please contact support.", ephemeral=True)

class SettingsView(discord.ui.View):
    """View for managing user notification settings."""
    def __init__(self, user_id: str, profile: Dict[str, Any]):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.profile = profile
        self.preferences = profile.get("preferences", {})

    @discord.ui.button(label="Toggle Proactive Notifications", style=discord.ButtonStyle.primary)
    async def toggle_proactive(self, interaction: discord.Interaction, button: discord.ui.Button):
        current = self.preferences.get("allow_proactive_notifications", True)
        new_val = not current
        self.preferences["allow_proactive_notifications"] = new_val
        self.profile["preferences"] = self.preferences
        
        # Save to DB (imported via a helper or direct ref if needed)
        # Note: bot.py has the save_user_profile logic, but views typically don't import bot.
        # We'll use the profile_db directly.
        from src.discord_bot.profile_db import get_profile_db
        db = get_profile_db()
        
        db.update_profile(self.user_id, preferences_json=self.preferences)
        
        status_text = "✅ Enabled" if new_val else "❌ Disabled"
        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="Proactive Notifications", value=f"Current status: {status_text}", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"Privacy settings updated: Proactive notifications are now {status_text.lower()}.", ephemeral=True)

class LogWorkoutView(ui.View):
    """
    Refined Interactive buttons for Fitness Agent recommendations (Phase 3).
    Supports proactive handoffs and cross-agent collaboration.
    """
    def __init__(self, bot: Any, data: Dict[str, Any], user_id: str):
        super().__init__(timeout=600)
        self.bot = bot
        self.data = data
        self.user_id = user_id
        
        # Handle both "recommendations" and "exercises" schemas
        self.recommendations = data.get("recommendations") or data.get("exercises") or []

    def _primary_exercise(self) -> Dict[str, Any]:
        if self.recommendations:
            return self.recommendations[0]
        return {"name": "Exercise", "duration_min": 20, "kcal_estimate": 80}

    @ui.button(label='Log Workout', style=discord.ButtonStyle.green, emoji='💪')
    async def log_workout(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("You can only log your own workouts!", ephemeral=True)
            
        exercise = self._primary_exercise()
        kcal = float(exercise.get("kcal_estimate") or exercise.get("calories") or 80)
        
        # PERSIST TO DB
        try:
            from src.discord_bot.profile_db import get_profile_db
            db = get_profile_db()
            db.log_workout_event(
                discord_user_id=self.user_id,
                exercise_name=exercise.get("name", "Exercise"),
                duration_min=int(exercise.get("duration_min") or exercise.get("duration") or 20),
                kcal_estimate=kcal,
                status="completed",
                source="fitness_button"
            )
        except Exception as e:
            logger.warning(f"Workout persistence failed: {e}")

        # Respond with standard confirmation + Handoff Suggestion
        embed = discord.Embed(
            title="🎯 Activity Logged!",
            description=f"Great job finishing **{exercise.get('name')}**!\nYou burned approximately **{kcal} kcal**.",
            color=discord.Color.green()
        )
        
        # Show the Handoff View for Nutrition
        await interaction.response.send_message(
            embed=embed,
            view=NutritionHandoffView(self.bot, self.user_id, kcal),
            ephemeral=False
        )
        
        # Disable the 'Log' button to prevent double-logging
        button.disabled = True
        await interaction.message.edit(view=self)

    @ui.button(label='Add To Routine', style=discord.ButtonStyle.blurple, emoji='📌')
    async def add_to_routine(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("📌 Added to your weekly routine!", ephemeral=True)

    @ui.button(label='View Progress', style=discord.ButtonStyle.gray, emoji='📈')
    async def view_progress(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This is for someone else!", ephemeral=True)
            
        try:
            from src.discord_bot.profile_db import get_profile_db
            db = get_profile_db()
            progress = db.get_workout_progress(self.user_id, days=7)
            
            msg = (
                "📈 **7-Day Progress**\n"
                f"• Suggested: **{progress.get('recommended_count', 0)}**\n"
                f"• Completed: **{progress.get('completed_count', 0)}**\n"
                f"• Active Min: **{progress.get('total_minutes', 0)}**\n"
                f"• Kcal Burned: **{progress.get('total_kcal', 0):.0f}**"
            )
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            logger.warning(f"Failed to fetch progress: {e}")
            await interaction.response.send_message("⚠️ Could not load progress.", ephemeral=True)

    @ui.button(label='Safety Info', style=discord.ButtonStyle.red, emoji='🛡️')
    async def safety_info(self, interaction: discord.Interaction, button: ui.Button):
        warnings = self.data.get("safety_warnings", [])
        msg = "**Safety Details**:\n" + ("\n".join([f"- {w}" for w in warnings]) if warnings else "No specific restrictions noted.")
        await interaction.response.send_message(msg, ephemeral=True)

class NutritionHandoffView(ui.View):
    """
    Proactive Bridge View (Fitness -> Nutrition).
    """
    def __init__(self, bot: Any, user_id: str, kcal_burned: float):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.kcal_burned = kcal_burned

    @ui.button(label='Check Recovery Nutrition', style=discord.ButtonStyle.secondary, emoji='🥗')
    async def check_nutrition(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This suggestion is for someone else!", ephemeral=True)
            
        await interaction.response.send_message("🔄 *Consulting Nutrition Agent for your recovery plan...*", ephemeral=True)
        
        # Use our new Swarm Signal
        from src.swarm import handoff_to_nutrition
        handoff_signal = handoff_to_nutrition(self.kcal_burned)
        
        # Trigger the swarmed response directly
        await self.bot._send_swarmed_response(
            interaction.channel,
            handoff_signal,
            self.user_id,
            scan_mode=False
        )
        
        # Disable button after use
        button.disabled = True
        await interaction.message.edit(view=self)

class MealServingAdjustModal(discord.ui.Modal, title="Adjust Serving"):
    """Modal to adjust the serving multiplier for a scanned meal."""

    multiplier = discord.ui.TextInput(
        label="Serving multiplier (e.g., 0.5, 1, 2)",
        placeholder="1",
        min_length=1,
        max_length=8,
    )
    dish_name = discord.ui.TextInput(
        label="Dish name override (optional)",
        placeholder="leave blank",
        required=False,
        min_length=0,
        max_length=80,
    )

    def __init__(self, view: "MealLogView"):
        self._view = view
        try:
            super().__init__()
        except RuntimeError:
            pass

    async def on_submit(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self._view.user_id):
            return await interaction.response.send_message("This meal is for someone else.", ephemeral=True)

        raw = str(getattr(self.multiplier, "value", "") or "").strip()
        try:
            m = float(raw)
        except Exception:
            return await interaction.response.send_message("Please enter a valid number (e.g., 0.5, 1, 2).", ephemeral=True)

        if m <= 0 or m > 10:
            return await interaction.response.send_message("Multiplier must be between 0 and 10.", ephemeral=True)

        dish_override = str(getattr(self.dish_name, "value", "") or "").strip()
        await self._view.apply_multiplier(interaction, m, dish_override=dish_override or None)

class OverTargetPromptView(discord.ui.View):
    def __init__(self, bot: 'HealthButlerDiscordBot', user_id: str, nutrition_payload: Dict[str, Any]):
        super().__init__(timeout=600)
        self.bot = bot
        self.user_id = str(user_id)
        self.nutrition_payload = nutrition_payload

    @discord.ui.button(label="Yes, help me", style=discord.ButtonStyle.blurple, emoji="🏃")
    async def on_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This is for someone else.", ephemeral=True)
            
        await interaction.response.send_message("🔄 *Let's get moving! Consulting Fitness Agent...*", ephemeral=True)
        
        try:
            from src.discord_bot.profile_utils import get_user_profile
            profile = get_user_profile(self.user_id)
            user_context = {
                "user_id": self.user_id,
                "name": profile.get("name", "User"),
                "conditions": profile.get("conditions", []),
                "nutrition_summary": json.dumps(self.nutrition_payload)
            }
            
            from src.swarm import handoff_to_fitness
            handoff_signal = handoff_to_fitness()
            
            result = await self.bot.swarm.execute_async(
                user_input=f"{handoff_signal}: My calories are over target today. Can you help me work it off?",
                user_context=user_context
            )
            
            await self.bot._send_swarmed_response(
                interaction.channel,
                result.get("response", "{}"),
                self.user_id,
                scan_mode=False
            )
            
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
            
        except Exception as e:
            logger.error(f"Error in OverTargetPrompt: {e}")
            await interaction.followup.send("❌ Error fetching workout plan. Try again later.", ephemeral=True)

    @discord.ui.button(label="No thanks", style=discord.ButtonStyle.gray, emoji="🚫")
    async def on_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This is for someone else.", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="👌 Got it. Let me know if you change your mind!", view=self)

class MealLogView(discord.ui.View):
    """Interactive controls to add/remove/adjust a scanned meal in daily totals."""

    def __init__(
        self,
        bot: 'HealthButlerDiscordBot',
        *,
        user_id: str,
        nutrition_payload: Dict[str, Any],
        logged_meal: Optional[Dict[str, Any]] = None,
    ):
        self.bot = bot
        self.user_id = str(user_id)
        self.nutrition_payload = nutrition_payload
        self.logged_meal = logged_meal or None

        try:
            super().__init__(timeout=3600)
        except RuntimeError:
            pass

        self._sync_button_states()

    def _sync_button_states(self) -> None:
        try:
            logged = self._is_logged()
            for item in getattr(self, "children", []) or []:
                if getattr(item, "label", None) == "Add to Today":
                    item.disabled = bool(logged)
                elif getattr(item, "label", None) == "Remove from Today":
                    item.disabled = not bool(logged)
        except Exception:
            pass

    def _is_logged(self) -> bool:
        return bool(self.logged_meal and self.logged_meal.get("meal_id"))

    async def _refresh_message_embed(self, interaction: discord.Interaction) -> None:
        embed = self.bot._build_nutrition_embed(self.nutrition_payload)
        if self._is_logged():
            embed.title = "✅ " + (embed.title or "Nutrition Analysis")
        else:
            embed.title = "📝 " + (embed.title or "Nutrition Analysis")
            embed.set_footer(text=(embed.footer.text + " • Not logged yet") if embed.footer and embed.footer.text else "Not logged yet")
        self._sync_button_states()
        await interaction.message.edit(embed=embed, view=self)

    async def apply_multiplier(self, interaction: discord.Interaction, multiplier: float, *, dish_override: Optional[str] = None) -> None:
        _apply_serving_multiplier(self.nutrition_payload, multiplier, dish_override=dish_override)
        meal_id = str((self.logged_meal or {}).get("meal_id") or "")

        if self._is_logged():
            from src.discord_bot import profile_utils as pu
            if pu.demo_mode and str(self.user_id) == str(pu.demo_user_id) and meal_id.startswith("demo-"):
                try:
                    macros = dict(self.nutrition_payload.get("total_macros", {}) or {})
                    meals = pu._demo_user_profile.get(self.user_id, {}).get("meals", []) or []
                    for m in meals:
                        if str(m.get("meal_id")) == meal_id:
                            m["dish"] = self.nutrition_payload.get("dish_name", m.get("dish"))
                            m["macros"] = macros
                            break
                    if isinstance(self.logged_meal, dict):
                        self.logged_meal["dish"] = self.nutrition_payload.get("dish_name", self.logged_meal.get("dish"))
                        self.logged_meal["macros"] = macros
                except Exception:
                    pass
            elif pu.profile_db and meal_id and not meal_id.startswith("demo-"):
                try:
                    macros = self.nutrition_payload.get("total_macros", {}) or {}
                    pu.profile_db.update_meal(
                        meal_id,
                        dish_name=self.nutrition_payload.get("dish_name"),
                        calories=float(macros.get("calories", 0) or 0),
                        protein_g=float(macros.get("protein", 0) or 0),
                        carbs_g=float(macros.get("carbs", 0) or 0),
                        fat_g=float(macros.get("fat", 0) or 0),
                    )
                    from datetime import date
                    pu.profile_db.recompute_daily_log_from_meals(self.user_id, date.today())
                except Exception as exc:
                    return await interaction.response.send_message(f"Failed to update meal: {exc}", ephemeral=True)

        await interaction.response.send_message("✅ Updated serving size.", ephemeral=True)
        await self._refresh_message_embed(interaction)
        await self.bot._send_daily_summary_embed(interaction.channel, self.user_id)

    def _build_meal_record(self) -> Dict[str, Any]:
        macros = self.nutrition_payload.get("total_macros", {}) or {}
        from src.discord_bot.profile_utils import LOCAL_TZ
        return {
            "time": datetime.now(LOCAL_TZ).strftime("%H:%M"),
            "dish": self.nutrition_payload.get("dish_name", "Meal"),
            "macros": {
                "calories": float(macros.get("calories", 0) or 0),
                "protein": float(macros.get("protein", 0) or 0),
                "carbs": float(macros.get("carbs", 0) or 0),
                "fat": float(macros.get("fat", 0) or 0),
            },
        }

    def _cache_add(self, record: Dict[str, Any]) -> None:
        try:
            from src.discord_bot.profile_utils import _user_profiles_cache
            if self.user_id in _user_profiles_cache:
                _user_profiles_cache[self.user_id].setdefault("meals", []).append(
                    {
                        "meal_id": record.get("meal_id"),
                        "time": record.get("time"),
                        "dish": record.get("dish"),
                        "macros": record.get("macros"),
                    }
                )
        except Exception:
            pass

    def _cache_remove(self, meal_id: str) -> None:
        try:
            from src.discord_bot.profile_utils import _user_profiles_cache
            if self.user_id in _user_profiles_cache:
                meals = _user_profiles_cache[self.user_id].get("meals", []) or []
                _user_profiles_cache[self.user_id]["meals"] = [m for m in meals if str(m.get("meal_id")) != str(meal_id)]
        except Exception:
            pass

    @discord.ui.button(label="Add to Today", style=discord.ButtonStyle.green, emoji="✅")
    async def add_to_today(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != str(self.user_id):
            return await interaction.response.send_message("This meal is for someone else.", ephemeral=True)

        if self._is_logged():
            return await interaction.response.send_message("Already logged.", ephemeral=True)

        record = self._build_meal_record()
        from src.discord_bot import profile_utils as pu

        if pu.demo_mode and str(self.user_id) == str(pu.demo_user_id):
            record["meal_id"] = f"demo-{uuid.uuid4().hex[:10]}"
            pu._demo_user_profile.setdefault(self.user_id, {"meals": []}).setdefault("meals", []).append(record)
            self.logged_meal = record
        elif pu.profile_db:
            try:
                created = pu.profile_db.create_meal(
                    discord_user_id=self.user_id,
                    dish_name=record["dish"],
                    calories=record["macros"]["calories"],
                    protein_g=record["macros"]["protein"],
                    carbs_g=record["macros"]["carbs"],
                    fat_g=record["macros"]["fat"],
                    confidence_score=float(self.nutrition_payload.get("confidence_score", 0.0) or 0.0),
                )
                meal_id = (created or {}).get("id")
                record["meal_id"] = meal_id or f"db-unknown-{uuid.uuid4().hex[:10]}"
                self.logged_meal = record
                from datetime import date
                pu.profile_db.recompute_daily_log_from_meals(self.user_id, date.today())
            except Exception as exc:
                return await interaction.response.send_message(f"Failed to log meal: {exc}", ephemeral=True)
        else:
            return await interaction.response.send_message("Database not connected; cannot log meals right now.", ephemeral=True)

        self._cache_add(record)
        await interaction.response.send_message("✅ Added to your daily total.", ephemeral=True)
        await self._refresh_message_embed(interaction)
        await self.bot._send_daily_summary_embed(interaction.channel, self.user_id)
        
        try:
            from src.discord_bot.profile_utils import get_user_profile, calculate_daily_target
            profile = get_user_profile(self.user_id)
            target = calculate_daily_target(profile)
            stats = pu.profile_db.get_today_stats(self.user_id) if pu.profile_db else {"total_calories": 0}
            consumed = stats.get("total_calories", 0) + float(record["macros"]["calories"])
            remaining = target - consumed
            
            if remaining < 0:
                prompt_msg = "⚠️ *You're over today's target. Would you like to discuss a quick burn-off plan?*"
                await interaction.channel.send(
                    prompt_msg, 
                    view=OverTargetPromptView(self.bot, self.user_id, self.nutrition_payload)
                )
        except Exception as e:
            logger.error(f"Error checking over-target during add_to_today: {e}")

    @discord.ui.button(label="Adjust Serving", style=discord.ButtonStyle.gray, emoji="✏️")
    async def adjust_serving(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != str(self.user_id):
            return await interaction.response.send_message("This meal is for someone else.", ephemeral=True)
        await interaction.response.send_modal(MealServingAdjustModal(self))

    @discord.ui.button(label="Remove from Today", style=discord.ButtonStyle.red, emoji="🗑️")
    async def remove_from_today(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != str(self.user_id):
            return await interaction.response.send_message("This meal is for someone else.", ephemeral=True)

        if not self._is_logged():
            return await interaction.response.send_message("This scan isn't logged yet.", ephemeral=True)

        meal_id = str(self.logged_meal.get("meal_id"))
        from src.discord_bot import profile_utils as pu

        if pu.demo_mode and str(self.user_id) == str(pu.demo_user_id):
            meals = pu._demo_user_profile.get(self.user_id, {}).get("meals", []) or []
            pu._demo_user_profile[self.user_id]["meals"] = [m for m in meals if str(m.get("meal_id")) != meal_id]
        elif pu.profile_db:
            try:
                pu.profile_db.delete_meal(meal_id)
                from datetime import date
                pu.profile_db.recompute_daily_log_from_meals(self.user_id, date.today())
            except Exception as exc:
                return await interaction.response.send_message(f"Failed to remove meal: {exc}", ephemeral=True)
        else:
            return await interaction.response.send_message("Database not connected; cannot remove meals right now.", ephemeral=True)

        self._cache_remove(meal_id)
        self.logged_meal = None
        await interaction.response.send_message("🗑️ Removed from your daily total.", ephemeral=True)
        await self._refresh_message_embed(interaction)
        await self.bot._send_daily_summary_embed(interaction.channel, self.user_id)
