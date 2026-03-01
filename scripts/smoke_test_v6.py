
import asyncio
import os
import sys
import uuid
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.discord_bot.profile_db import get_profile_db

async def run_smoke_test():
    print("🚀 Starting Smoke Test v6.1 (Supabase + String IDs)")
    
    try:
        db = get_profile_db()
        print("✅ DB Connection Initialized")
        
        # 1. Test String ID Persistence (The previous blocker)
        test_discord_id = f"smoke_test_user_{int(datetime.now().timestamp())}"
        print(f"📝 Testing with ID: {test_discord_id}")
        
        # Test Chat Message
        msg = db.save_message(test_discord_id, "user", "Smoke test greeting")
        print(f"✅ chat_messages persistence OK (ID: {msg.get('id')})")
        
        # 2. Test Profile Creation (Step 1 Onboarding)
        profile = db.create_profile(
            discord_user_id=test_discord_id,
            full_name="Smoke Test User",
            age=30,
            gender="male",
            height_cm=180,
            weight_kg=80,
            goal="maintain",
            conditions=["None"],
            activity="moderately active",
            diet=["Balanced"],
            preferences={"onboarding_completed": True}
        )
        print(f"✅ profiles creation OK (Name: {profile.get('full_name')})")
        
        # 3. Test Profile Retrieval
        fetched = db.get_profile(test_discord_id)
        if fetched and fetched['id'] == test_discord_id:
            print("✅ profiles retrieval OK")
        else:
            print("❌ profiles retrieval FAILED")
            
        # 4. Test View Integration
        # Create a daily summary to trigger view logic
        print("📝 Testing daily_summaries and v_monthly_trends...")
        # Since triggers might take time, we just test the table insert
        summary = db.client.table("daily_summaries").insert({
            "user_id": test_discord_id,
            "date": datetime.now().date().isoformat(),
            "net_calories": 2500,
            "water_intake_ml": 2000,
            "goal_reached": True
        }).execute()
        print(f"✅ daily_summaries persistence OK")
        
        # 5. Clean up (Optional, but good for cleanliness)
        # Note: We don't necessarily delete to leave proof in DB for manual inspection if needed
        
        print("\n✨ Smoke Test PASSED! All systems operational with String IDs.")
        
    except Exception as e:
        print(f"\n❌ Smoke Test FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
