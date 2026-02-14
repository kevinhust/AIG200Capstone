"""Targeted persistence tests for Discord demo flow and Supabase writes."""

import asyncio
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock


def _ensure_test_stubs() -> None:
	"""Provide lightweight stubs for optional runtime dependencies in tests."""
	try:
		# Force deterministic discord stubs for these unit tests, even if the
		# real discord.py package is installed in the environment.
		raise ImportError("force discord stubs for tests")
		import discord  # noqa: F401
	except Exception:
		discord_stub = types.ModuleType("discord")

		class _Client:
			def __init__(self, *args, **kwargs):
				return None

		class _Intents:
			message_content = True
			messages = True
			guilds = True

			@staticmethod
			def default():
				return _Intents()

		class _Embed:
			def __init__(self, *args, **kwargs):
				return None

			def add_field(self, *args, **kwargs):
				return None

			def set_footer(self, *args, **kwargs):
				return None

		class _View:
			def __init__(self, *args, **kwargs):
				return None

		class _Modal:
			def __init_subclass__(cls, **kwargs):
				return None

		class _TextInput:
			def __init__(self, *args, **kwargs):
				self.value = ""

		class _ButtonStyle:
			green = 1
			blurple = 2
			gray = 3
			red = 4

		class _ActivityType:
			listening = 1

		class _Activity:
			def __init__(self, *args, **kwargs):
				return None

		class _Color:
			@staticmethod
			def green():
				return 0

			@staticmethod
			def blurple():
				return 0

			@staticmethod
			def blue():
				return 0

		def _button(*args, **kwargs):
			def _decorator(func):
				return func
			return _decorator

		def _select(*args, **kwargs):
			def _decorator(func):
				return func
			return _decorator

		class _SelectOption:
			def __init__(self, *args, **kwargs):
				return None

		discord_stub.Client = _Client
		discord_stub.Intents = _Intents
		discord_stub.Embed = _Embed
		discord_stub.ButtonStyle = _ButtonStyle
		discord_stub.ActivityType = _ActivityType
		discord_stub.Activity = _Activity
		discord_stub.Color = _Color
		discord_stub.SelectOption = _SelectOption
		discord_stub.Interaction = object
		discord_stub.Message = object
		discord_stub.ui = types.SimpleNamespace(
			View=_View,
			Modal=_Modal,
			TextInput=_TextInput,
			Button=object,
			Select=object,
			button=_button,
			select=_select,
		)

		ext_module = types.ModuleType("discord.ext")
		commands_module = types.ModuleType("discord.ext.commands")
		tasks_module = types.ModuleType("discord.ext.tasks")

		def _loop(*args, **kwargs):
			def _decorator(func):
				async def _wrapped(*f_args, **f_kwargs):
					return await func(*f_args, **f_kwargs)

				_wrapped.start = lambda *a, **k: None
				return _wrapped

			return _decorator

		tasks_module.loop = _loop

		sys.modules["discord"] = discord_stub
		sys.modules["discord.ext"] = ext_module
		sys.modules["discord.ext.commands"] = commands_module
		sys.modules["discord.ext.tasks"] = tasks_module

	# Only stub health_butler.swarm when it is genuinely unavailable.
	# Stubbing unconditionally (based on sys.modules) can break other tests that
	# exercise the real HealthSwarm/MessageBus implementations.
	try:
		import health_butler.swarm  # noqa: F401
	except Exception:
		swarm_module = types.ModuleType("health_butler.swarm")

		class _HealthSwarm:
			def __init__(self, *args, **kwargs):
				return None

			def execute(self, *args, **kwargs):
				return {"response": "{}", "delegations": [], "message_log": []}

		swarm_module.HealthSwarm = _HealthSwarm
		sys.modules["health_butler.swarm"] = swarm_module

	try:
		import supabase  # noqa: F401
	except Exception:
		profile_db_module = types.ModuleType("health_butler.discord_bot.profile_db")

		class _ProfileDB:
			pass

		def _get_profile_db():
			return None

		profile_db_module.ProfileDB = _ProfileDB
		profile_db_module.get_profile_db = _get_profile_db
		sys.modules["health_butler.discord_bot.profile_db"] = profile_db_module

	try:
		import aiohttp  # noqa: F401
	except Exception:
		aiohttp_module = types.ModuleType("aiohttp")

		class _Application:
			def __init__(self, *args, **kwargs):
				self.router = types.SimpleNamespace(add_get=lambda *a, **k: None)

		class _Response:
			def __init__(self, *args, **kwargs):
				return None

		class _AppRunner:
			def __init__(self, *args, **kwargs):
				return None

			async def setup(self):
				return None

		class _TCPSite:
			def __init__(self, *args, **kwargs):
				return None

			async def start(self):
				return None

		aiohttp_module.web = types.SimpleNamespace(
			Application=_Application,
			Response=_Response,
			AppRunner=_AppRunner,
			TCPSite=_TCPSite,
		)
		sys.modules["aiohttp"] = aiohttp_module


_ensure_test_stubs()

from health_butler.discord_bot import bot as discord_bot


def test_save_user_profile_create_writes_typed_profile_fields() -> None:
	"""Demo onboarding profile payload should map to Supabase profile types/columns."""
	mock_db = MagicMock()
	mock_db.get_profile.return_value = None
	discord_bot.profile_db = mock_db
	discord_bot._user_profiles_cache.clear()

	ok = discord_bot.save_user_profile(
		"12345",
		{
			"name": "Aziz",
			"age": "29",
			"gender": "Male",
			"height": "178",
			"weight": "82.5",
			"goal": "Lose Weight",
			"conditions": ["Diabetes"],
			"activity": "Lightly Active",
			"diet": ["Vegan"],
		},
	)

	assert ok is True
	assert mock_db.create_profile.call_count == 1

	kwargs = mock_db.create_profile.call_args.kwargs
	assert kwargs["discord_user_id"] == "12345"
	assert kwargs["full_name"] == "Aziz"
	assert isinstance(kwargs["age"], int)
	assert kwargs["age"] == 29
	assert isinstance(kwargs["height_cm"], float)
	assert kwargs["height_cm"] == 178.0
	assert isinstance(kwargs["weight_kg"], float)
	assert kwargs["weight_kg"] == 82.5
	assert kwargs["gender"] == "Male"
	assert kwargs["activity"] == "Lightly Active"
	assert kwargs["diet"] == ["Vegan"]
	assert kwargs["preferences"] == {}


def test_save_user_profile_update_writes_supported_columns() -> None:
	"""Existing profile updates should include all mapped Supabase columns."""
	mock_db = MagicMock()
	mock_db.get_profile.return_value = {"id": "12345"}
	discord_bot.profile_db = mock_db

	ok = discord_bot.save_user_profile(
		"12345",
		{
			"name": "Aziz",
			"age": 30,
			"gender": "Male",
			"height": 180,
			"weight": 84,
			"goal": "Maintain",
			"conditions": ["None"],
			"activity": "Moderately Active",
			"diet": ["None"],
		},
	)

	assert ok is True
	assert mock_db.update_profile.call_count == 1

	args = mock_db.update_profile.call_args.args
	kwargs = mock_db.update_profile.call_args.kwargs
	assert args[0] == "12345"
	assert kwargs["full_name"] == "Aziz"
	assert kwargs["age"] == 30
	assert kwargs["gender"] == "Male"
	assert kwargs["height_cm"] == 180.0
	assert kwargs["weight_kg"] == 84.0
	assert kwargs["goal"] == "Maintain"
	assert kwargs["restrictions"] is None
	assert kwargs["activity"] == "Moderately Active"
	assert kwargs["diet"] is None
	assert kwargs["preferences_json"] == {}


def test_persist_chat_message_writes_chat_messages_payload() -> None:
	"""Chat persistence helper should write user_id/role/content as strings."""
	mock_db = MagicMock()
	discord_bot.profile_db = mock_db

	client = discord_bot.HealthButlerDiscordBot.__new__(discord_bot.HealthButlerDiscordBot)
	client._persist_chat_message(user_id=12345, role="assistant", content={"msg": "hello"})

	assert mock_db.save_message.call_count == 1
	kwargs = mock_db.save_message.call_args.kwargs
	assert kwargs["discord_user_id"] == "12345"
	assert kwargs["role"] == "assistant"
	assert isinstance(kwargs["content"], str)


def test_persist_meal_data_writes_daily_logs_and_meals_with_numeric_values() -> None:
	"""Meal persistence should write numeric-compatible values for daily_logs and meals."""
	mock_db = MagicMock()
	discord_bot.profile_db = mock_db
	discord_bot.demo_mode = False
	discord_bot.demo_user_id = None
	discord_bot._user_profiles_cache.clear()

	client = discord_bot.HealthButlerDiscordBot.__new__(discord_bot.HealthButlerDiscordBot)
	client._extract_json_payload = lambda _: {
		"dish_name": "Avocado",
		"total_macros": {
			"calories": "299.0",
			"protein": "1.3",
			"carbs": "5.2",
			"fat": "30.3",
		},
		"confidence_score": 0.9,
	}

	meal_record = asyncio.run(client._persist_meal_data("{}", "u-1"))

	assert meal_record is not None
	assert mock_db.create_daily_log.call_count == 1
	assert mock_db.create_meal.call_count == 1

	daily_kwargs = mock_db.create_daily_log.call_args.kwargs
	assert daily_kwargs["discord_user_id"] == "u-1"
	assert isinstance(daily_kwargs["calories_intake"], float)
	assert isinstance(daily_kwargs["protein_g"], float)

	meal_kwargs = mock_db.create_meal.call_args.kwargs
	assert meal_kwargs["discord_user_id"] == "u-1"
	assert meal_kwargs["dish_name"] == "Avocado"
	assert isinstance(meal_kwargs["calories"], float)
	assert isinstance(meal_kwargs["protein_g"], float)
	assert isinstance(meal_kwargs["carbs_g"], float)
	assert isinstance(meal_kwargs["fat_g"], float)


def test_demo_diet_step_saves_profile_to_supabase() -> None:
	"""Final demo setup step should persist profile through save_user_profile."""
	discord_bot._demo_user_profile.clear()
	discord_bot.demo_mode = False
	discord_bot.demo_user_id = None

	user_id = "98765"
	discord_bot._demo_user_profile[user_id] = {
		"name": "Aziz",
		"age": 30,
		"gender": "Male",
		"height": 178.0,
		"weight": 82.0,
		"goal": "Maintain",
		"conditions": [],
		"activity": "Lightly Active",
		"meals": [],
	}

	save_spy = MagicMock(return_value=True)
	original_save_user_profile = discord_bot.save_user_profile
	discord_bot.save_user_profile = save_spy

	view = discord_bot.DietSelectView(user_id)

	class _Response:
		async def edit_message(self, *args, **kwargs):
			return None

		async def send_message(self, *args, **kwargs):
			return None

	class _Client:
		async def change_presence(self, *args, **kwargs):
			return None

	interaction = SimpleNamespace(
		user=SimpleNamespace(id=int(user_id), display_name="Aziz"),
		response=_Response(),
		client=_Client(),
	)
	select = SimpleNamespace(values=["Vegetarian"])

	try:
		asyncio.run(view.select_diet(interaction, select))

		assert discord_bot.demo_mode is True
		assert discord_bot.demo_user_id == user_id
		assert save_spy.call_count == 1
		assert save_spy.call_args.args[0] == user_id
		assert save_spy.call_args.args[1]["diet"] == ["Vegetarian"]
	finally:
		discord_bot.save_user_profile = original_save_user_profile


def test_personalization_modal_finalizes_profile_with_preferences() -> None:
	"""Step 6 modal should persist preferences and keep datatype-safe values."""
	discord_bot._demo_user_profile.clear()
	discord_bot.demo_mode = False
	discord_bot.demo_user_id = None

	user_id = "112233"
	discord_bot._demo_user_profile[user_id] = {
		"name": "Aziz",
		"age": 30,
		"gender": "Male",
		"height": 178.0,
		"weight": 82.0,
		"goal": "Maintain",
		"conditions": [],
		"activity": "Lightly Active",
		"diet": ["Vegetarian"],
		"meals": [],
	}

	save_spy = MagicMock(return_value=True)
	original_save_user_profile = discord_bot.save_user_profile
	discord_bot.save_user_profile = save_spy

	modal = discord_bot.PersonalizationModal(user_id)
	modal.sleep_hours.value = "7.5"
	modal.stress_level.value = "4"
	modal.workout_days_per_week.value = "5"
	modal.session_minutes.value = "40"
	modal.motivation_style.value = "balanced"

	class _Response:
		async def send_message(self, *args, **kwargs):
			return None

	class _Client:
		async def change_presence(self, *args, **kwargs):
			return None

	interaction = SimpleNamespace(
		user=SimpleNamespace(id=int(user_id), display_name="Aziz"),
		response=_Response(),
		client=_Client(),
	)

	try:
		asyncio.run(modal.on_submit(interaction))

		assert discord_bot.demo_mode is True
		assert discord_bot.demo_user_id == user_id
		assert save_spy.call_count == 1

		saved_profile = save_spy.call_args.args[1]
		prefs = saved_profile["preferences"]
		assert isinstance(prefs["sleep_hours"], float)
		assert isinstance(prefs["stress_level"], int)
		assert isinstance(prefs["workout_days_per_week"], int)
		assert isinstance(prefs["session_minutes"], int)
		assert prefs["motivation_style"] == "balanced"
	finally:
		discord_bot.save_user_profile = original_save_user_profile


def test_create_profile_fallback_when_preferences_json_missing() -> None:
	"""Profile creation should retry without preferences_json on older schema."""
	mock_db = MagicMock()
	mock_db.get_profile.return_value = None

	create_calls = []

	def _create_profile(**kwargs):
		create_calls.append(kwargs)
		if len(create_calls) == 1:
			raise Exception("column preferences_json does not exist")
		return {"id": "u-legacy"}

	mock_db.create_profile.side_effect = _create_profile
	discord_bot.profile_db = mock_db

	ok = discord_bot.save_user_profile(
		"u-legacy",
		{
			"name": "Legacy",
			"age": 28,
			"gender": "Male",
			"height": 175,
			"weight": 75,
			"goal": "Maintain",
			"conditions": [],
			"activity": "Moderately Active",
			"diet": ["None"],
			"preferences": {"sleep_hours": 7.0},
		},
	)

	# save_user_profile should still succeed because ProfileDB now retries without preferences_json
	assert ok is True


def test_update_profile_fallback_when_preferences_json_missing() -> None:
	"""Profile update should retry without preferences_json on older schema."""
	mock_db = MagicMock()
	mock_db.get_profile.return_value = {"id": "u-legacy"}

	update_attempts = {"count": 0}

	def _update_profile(_user_id, **kwargs):
		update_attempts["count"] += 1
		if update_attempts["count"] == 1:
			raise Exception("column preferences_json does not exist")
		return {"id": "u-legacy"}

	mock_db.update_profile.side_effect = _update_profile
	discord_bot.profile_db = mock_db

	ok = discord_bot.save_user_profile(
		"u-legacy",
		{
			"name": "Legacy",
			"age": 28,
			"gender": "Male",
			"height": 175,
			"weight": 75,
			"goal": "Maintain",
			"conditions": [],
			"activity": "Moderately Active",
			"diet": ["None"],
			"preferences": {"sleep_hours": 7.0},
		},
	)

	assert ok is True
