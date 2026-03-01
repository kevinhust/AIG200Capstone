import asyncio
import json
# Mock discord if not available
try:
    import discord
except ImportError:
    class MockColor:
        @staticmethod
        def green(): return 0x00ff00
        @staticmethod
        def orange(): return 0xffa500
        @staticmethod
        def red(): return 0xff0000
        @staticmethod
        def blue(): return 0x0000ff
        @staticmethod
        def dark_teal(): return 0x008080

    class MockEmbed:
        def __init__(self, **kwargs):
            self.title = kwargs.get("title")
            self.description = kwargs.get("description")
            self.color = kwargs.get("color")
            self.fields = []
            self.footer = None
        def add_field(self, **kwargs): self.fields.append(type('Field', (), kwargs))
        def set_footer(self, **kwargs): self.footer = kwargs.get("text")
        def set_image(self, **kwargs): pass

    import sys
    from unittest.mock import MagicMock
    mock_discord = MagicMock()
    mock_discord.Embed = MockEmbed
    mock_discord.Color = MockColor
    sys.modules["discord"] = mock_discord

# Mock supabase if not available
try:
    from supabase import create_client, Client
except ImportError:
    import sys
    from unittest.mock import MagicMock
    mock_supabase = MagicMock()
    mock_supabase.create_client = MagicMock()
    sys.modules["supabase"] = mock_supabase

from src.discord_bot.profile_db import get_profile_db
from src.agents.analytics.analytics_agent import AnalyticsAgent
from src.discord_bot.embed_builder import HealthButlerEmbed

async def verify_phase_5():
    print("🚀 Verifying Phase 5: AnalyticsAgent Upgrade...")
    
    db = get_profile_db()
    agent = AnalyticsAgent()
    user_id = "cd02c5f7-32dd-4a90-b903-9f5b5cfc1938" # Sample user from earlier query
    
    # 1. Test ProfileDB View Query
    print(f"\n1. Testing ProfileDB.get_monthly_trends_raw for {user_id}...")
    trends = db.get_monthly_trends_raw(user_id)
    print(f"   Results: {len(trends)} days of data found.")
    
    # 2. Test AnalyticsAgent sparkline support
    print("\n2. Testing AnalyticsAgent.analyze_trends with mock data...")
    mock_historical = [
        {"date": "2026-02-20", "avg_calories": 2100, "total_water": 1500},
        {"date": "2026-02-21", "avg_calories": 1900, "total_water": 2000},
        {"date": "2026-02-22", "avg_calories": 2500, "total_water": 1000},
        {"date": "2026-02-23", "avg_calories": 1800, "total_water": 2500},
    ]
    mock_profile = {"name": "Kevin", "age": 25, "gender": "male", "weight_kg": 70, "height_cm": 175, "activity": "moderately active", "goal": "maintain"}
    
    analysis = await agent.analyze_trends(mock_historical, mock_profile)
    print("   Analysis Sparklines:", analysis.get("sparklines"))
    
    # 3. Test EmbedBuilder visualization
    print("\n3. Testing HealthButlerEmbed.build_trends_embed...")
    embed = HealthButlerEmbed.build_trends_embed("Kevin", analysis, mock_historical)
    print(f"   Embed Fields: {len(embed.fields)}")
    for field in embed.fields:
        print(f"   - {field.name}: {field.value}")

    print("\n✅ Verification Script Completed.")

if __name__ == "__main__":
    asyncio.run(verify_phase_5())
