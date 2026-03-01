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
        
        # Heuristic: Only suggest foods that fit within 80% of remaining budget
        # or have a low calorie floor (50) to avoid suggesting nothing.
        eligible_pool = [
            f for f in self.food_pool 
            if f["calories"] <= max(100, remaining_cals * 0.8)
        ]
        
        if not eligible_pool:
            eligible_pool = [f for f in self.food_pool if f["calories"] < 200]
            
        # 2. Animation loop
        rolling_emojis = ["🥗", "🍎", "🍗", "🍱", "🍣", "🥑", "🥦", "🍓", "🥩", "🥚", "🍲", "🍤"]
        for i in range(6):
            emoji = random.choice(rolling_emojis)
            await interaction.edit_original_response(content=f"🎰 **The Roulette is spinning...** {emoji}")
            await asyncio.sleep(0.4)
            
        # 3. Final Selection
        final_choice = random.choice(eligible_pool)
        
        # 4. Result Embed
        embed = discord.Embed(
            title="🎯 Your Healthy Inspiration",
            description=(
                f"The roulette has spoken! How about this for your next meal?\n\n"
                f"## {final_choice['emoji']} {final_choice['name']}\n"
                f"🔥 ~**{final_choice['calories']}** kcal\n"
                f"✨ Tags: {', '.join(final_choice['tags'])}\n\n"
                f"*Fits perfectly into your remaining **{int(remaining_cals)}** kcal budget!*"
            ),
            color=discord.Color.gold()
        )
        
        # Add tips based on tags
        tips = {
            "protein": "Great for muscle recovery!",
            "fiber": "Helps you stay full longer.",
            "low-cal": "Light and refreshing choice!",
            "fat": "Important for hormone health.",
        }
        for tag in final_choice['tags']:
            if tag in tips:
                embed.add_field(name="💡 Butler's Tip", value=tips[tag], inline=False)
                break
        
        embed.set_footer(text="Personal Health Butler AI • Premium Health Companion")
        
        await interaction.edit_original_response(content=None, embed=embed, view=None)

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
