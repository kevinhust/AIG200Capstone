import discord
from datetime import datetime
from typing import Dict, Any, List

class HealthButlerEmbed:
    """
    Centralized factory for creating consistent, premium Discord Embeds
    for the Health Butler Bot.
    """
    COLOR_MAP = {
        "fitness": discord.Color.green(),
        "nutrition": discord.Color.orange(),
        "warning": discord.Color.red(),
        "info": discord.Color.blue(),
        "summary": discord.Color.dark_teal()
    }

    @staticmethod
    def build_fitness_card(data: Dict[str, Any], user_name: str = "User") -> discord.Embed:
        """
        Builds a rich fitness recommendation card with exercise images.
        """
        embed = discord.Embed(
            title=f"🏃 Fitness Plan: {user_name}",
            description=data.get("summary", "Personalized workout recommendations based on your profile."),
            color=HealthButlerEmbed.COLOR_MAP["fitness"],
            timestamp=datetime.utcnow()
        )

        # Handle both "recommendations" (specialist agent) and "exercises" (legacy/RAG direct)
        recs = data.get("recommendations") or data.get("exercises") or []
        
        main_image = None
        
        for i, ex in enumerate(recs[:5], 1):
            name = ex.get("name", "Exercise")
            
            # Extract attributes based on schema flexibility
            duration = ex.get("duration_min") or ex.get("duration")
            kcal = ex.get("kcal_estimate") or ex.get("calories")
            reason = ex.get("reason") or ex.get("description")
            
            muscles = ", ".join(ex.get("target_muscles", [])) if ex.get("target_muscles") else None
            
            details = []
            if duration: details.append(f"⏱️ **{duration} min**")
            if kcal: details.append(f"🔥 **{kcal} kcal**")
            if muscles: details.append(f"🎯 **{muscles}**")
            
            value = " | ".join(details) if details else "Custom recommended activity"
            if reason:
                value += f"\n*\"{reason}\"*"
            
            embed.add_field(name=f"{i}. {name}", value=value, inline=False)
            
            # Grab the first valid image URL for the main preview
            if not main_image and ex.get("image_url"):
                main_image = ex["image_url"]

        # Safety & Precautions
        warnings = data.get("safety_warnings", [])
        if warnings:
            embed.add_field(name="🛡️ Safety Precautions", value="\n".join([f"• {w}" for w in warnings]), inline=False)

        # Main Image (Prominent display)
        if main_image:
            embed.set_image(url=main_image)
        
        embed.set_footer(text="Powered by Health Butler RAG • Premium Media Integration")
        return embed

    @staticmethod
    def build_error_embed(message: str) -> discord.Embed:
        return discord.Embed(
            title="⚠️ System Notice",
            description=message,
            color=HealthButlerEmbed.COLOR_MAP["warning"]
        )

    @staticmethod
    def build_progress_embed(step: int, total_steps: int, title: str, description: str) -> discord.Embed:
        """
        Builds a consistent progress embed with a visual bar.
        Example: Step 1/3 🟢⚪⚪
        """
        filled = "🟢" * step
        empty = "⚪" * (total_steps - step)
        progress_bar = f"{filled}{empty}"
        
        embed = discord.Embed(
            title=f"Step {step}/{total_steps}: {title} {progress_bar}",
            description=description,
            color=HealthButlerEmbed.COLOR_MAP["info"]
        )
        embed.set_footer(text="v4.1 Mobile Optimized Onboarding")
        return embed

    @staticmethod
    def build_trends_embed(user_name: str, trend_data: Dict[str, Any], historical_raw: List[Dict[str, Any]]) -> discord.Embed:
        """
        Builds a comprehensive health trends report with sparkline visuals.
        """
        embed = discord.Embed(
            title=f"📈 Periodic Health Report: {user_name}",
            description=trend_data.get("trend_summary", "Your long-term performance analyzed."),
            color=HealthButlerEmbed.COLOR_MAP["summary"],
            timestamp=datetime.utcnow()
        )

        # 1. Visualization (Sparklines)
        cal_in = [d.get("calories_in", 0) for d in historical_raw]
        active_min = [d.get("active_minutes", 0) for d in historical_raw]
        
        cal_spark = HealthButlerEmbed._generate_sparkline(cal_in)
        act_spark = HealthButlerEmbed._generate_sparkline(active_min)

        embed.add_field(name="🍎 Calorie Intake (30d)", value=f"`{cal_spark}`", inline=False)
        embed.add_field(name="⚡ Active Minutes (30d)", value=f"`{act_spark}`", inline=False)

        # 2. Key Metrics
        stats = trend_data.get("weekly_stats", {})
        indicators = trend_data.get("status_indicators", {})
        
        cal_trend = "↗️ Improving" if indicators.get("calories") == "improving" else "↘️ Declining" if indicators.get("calories") == "declining" else "➡️ Stable"
        act_trend = "↗️ Improving" if indicators.get("activity") == "improving" else "↘️ Declining" if indicators.get("activity") == "declining" else "➡️ Stable"

        embed.add_field(name="Weekly Avg Net", value=f"{stats.get('avg_net_calories', 0):.0f} kcal ({cal_trend})", inline=True)
        embed.add_field(name="Weekly Avg Activity", value=f"{stats.get('avg_active_minutes', 0)} min ({act_trend})", inline=True)
        
        # 3. Forecast
        forecast = trend_data.get("goal_forecast", {})
        embed.add_field(
            name="🏁 Goal Forecast", 
            value=f"Target Date: **{forecast.get('estimated_date', 'N/A')}**\nConfidence: `{forecast.get('confidence', 'medium').capitalize()}`\n*{forecast.get('insight', '')}*",
            inline=False
        )

        # 4. Anomalies
        anomalies = trend_data.get("anomalies", [])
        if anomalies:
            embed.add_field(name="🚨 Alerts", value="\n".join([f"• {a}" for a in anomalies]), inline=False)

        embed.set_footer(text="Analytics Engine v1.0 • Predictive Health Forecasting")
        return embed

    @staticmethod
    def _generate_sparkline(data: List[float], bins: int = 8) -> str:
        """Generates a Unicode block sparkline."""
        if not data: return "No data"
        blocks = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        low = min(data)
        high = max(data)
        
        if high == low:
            return blocks[4] * len(data)
            
        line = ""
        for v in data:
            idx = int(((v - low) / (high - low)) * (len(blocks) - 1))
            line += blocks[idx]
        return line
