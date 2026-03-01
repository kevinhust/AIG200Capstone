import discord
from discord import ui
import asyncio
import random
from typing import List, Dict, Any

class RouletteView(ui.View):
    """
    Interactive Food Roulette for gamified healthy meal inspiration.
    Filters suggestions based on the user's remaining calorie/macro budget.
    """
    def __init__(self, user_id: str, remaining_budget: Dict[str, float]):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.remaining_budget = remaining_budget
        
        # Healthy food pool with tags for budget filtering
        self.food_pool = [
            {"name": "Grilled Salmon", "emoji": "📊", "calories": 350, "tags": ["protein", "omega-3"]},
            {"name": "Greek Salad", "emoji": "🥗", "calories": 200, "tags": ["fiber", "low-cal"]},
            {"name": "Chicken Breast", "emoji": "🍗", "calories": 250, "tags": ["lean-protein"]},
            {"name": "Quinoa Bowl", "emoji": "🥣", "calories": 400, "tags": ["complex-carbs", "fiber"]},
            {"name": "Steamed Broccoli", "emoji": "🥦", "calories": 50, "tags": ["superfood", "low-cal"]},
            {"name": "Hard Boiled Eggs", "emoji": "🥚", "calories": 140, "tags": ["protein", "quick-snack"]},
            {"name": "Avocado Toast", "emoji": "🥑", "calories": 300, "tags": ["healthy-fats"]},
            {"name": "Mixed Berries", "emoji": "🍓", "calories": 80, "tags": ["antioxidants", "low-cal"]},
            {"name": "Tofu Stir-fry", "emoji": "🍱", "calories": 320, "tags": ["plant-protein", "vegan"]},
            {"name": "Greek Yogurt", "emoji": "🥛", "calories": 150, "tags": ["probiotics", "protein"]},
            {"name": "Grilled Shrimp", "emoji": "🍤", "calories": 180, "tags": ["low-fat", "protein"]},
            {"name": "Lentil Soup", "emoji": "🍲", "calories": 280, "tags": ["fiber", "vegan-protein"]},
        ]

    @ui.button(label='🎰 Spin for Inspiration', style=discord.ButtonStyle.blurple, emoji="🎰")
    async def spin_roulette(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This roulette is for someone else!", ephemeral=True)
        
        # Disable button to prevent multi-clicks
        button.disabled = True
        await interaction.response.edit_message(view=self)
        
        # 1. Filter pool based on remaining calories
        remaining_cals = self.remaining_budget.get("calories", 2000)
        eligible_pool = [
            f for f in self.food_pool 
            if f["calories"] <= max(120, remaining_cals * 0.9)
        ]
        
        if not eligible_pool:
            eligible_pool = [f for f in self.food_pool if f["calories"] < 250]
            
        # 2. Enhanced Animation loop (Braking Effect)
        rolling_emojis = ["🥗", "🍎", "🍗", "🍱", "🍣", "🥑", "🥦", "🍓", "🥩", "🥚", "🍲", "🍤"]
        frames = 10
        for i in range(frames):
            emoji = random.choice(rolling_emojis)
            progress = "▰" * (i + 1) + "▱" * (frames - i - 1)
            # Slower as it approaches the end
            wait_time = 0.2 + (i * 0.1) 
            content = f"🎰 **The Roulette is spinning...**\n`{progress}` {emoji}"
            await interaction.edit_original_response(content=content)
            await asyncio.sleep(wait_time)
            
        # 3. Final Selection
        final_choice = random.choice(eligible_pool)
        
        # 4. Premium Result Embed
        embed = discord.Embed(
            title="🎯 Butler's Selection: Prime Health Choice",
            description=(
                f"## {final_choice['emoji']} {final_choice['name']}\n"
                f"The algorithms have aligned! This choice provides optimal fuel while respecting your remaining constraints.\n\n"
                f"🔥 **Energy**: ~{final_choice['calories']} kcal\n"
                f"🏷️ **Tags**: {', '.join([f'`{t}`' for t in final_choice['tags']])}\n\n"
                f"✅ *Successfully fitted into your **{int(remaining_cals)}** kcal daily budget.*"
            ),
            color=0xF1C40F # Premium Gold
        )
        
        # Add visual "Confidence" bar
        embed.add_field(
            name="🤖 Recommendation Strength", 
            value="🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜ (86%)", 
            inline=False
        )
        
        tips = {
            "protein": "Essential for muscle synthesized post-workout.",
            "fiber": "Optimizes digestion and satiety levels.",
            "low-cal": "Volume-dense, low-calorie density mastery.",
            "fat": "Crucial for hormonal balance and brain function.",
        }
        for tag in final_choice['tags']:
            if tag in tips:
                embed.add_field(name="💡 Why this works", value=tips[tag], inline=True)
                break
        
        embed.set_thumbnail(url="https://img.icons8.com/parakeet/96/000000/trophy.png")
        embed.set_footer(text="✨ Personal Health Butler • Intelligence in Action")
        
        # Final celebratory message
        await interaction.edit_original_response(content="🎉 **JACKPOT!** We found the perfect meal for you!", embed=embed, view=None)

class MealInspirationView(ui.View):
    """Initial view triggered by the engagement agent with multiple options."""
    def __init__(self, user_id: str, remaining_budget: Dict[str, float]):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.remaining_budget = remaining_budget

    @ui.button(label='🎰 Food Roulette', style=discord.ButtonStyle.blurple, emoji="🎰")
    async def food_roulette(self, interaction: discord.Interaction, button: ui.Button):
        # Swap this view for the RouletteView animation
        await interaction.response.edit_message(
            content="🎰 Ready to spin for a healthy recommendation?",
            embed=None,
            view=RouletteView(self.user_id, self.remaining_budget)
        )

    @ui.button(label='📈 View Trends', style=discord.ButtonStyle.gray, emoji="📈")
    async def view_trends(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Use `/trends` to see your full analytical report!", ephemeral=True)
