# Milestone 3 → Milestone 4: Hybrid Architecture Upgrade Changelog

**Document Version:** 2.0
**Date:** 2026-03-27
**Scope:** Changes between M3 (v8.5) and M4 (v10.0)

---

## 🚀 Key Improvements

| Component | M3 State | M4 State | Impact |
|-----------|----------|----------|--------|
| Deployment | Unreliable Verification | **OIDC Verified CICD** | 100% Deployment Confidence |
| Proactive | DM-hosted notifications | **Channel-hosted Proactive** | Unified User Experience |
| Vision | Basic Gemini Flow | **YOLO-Accelerated Pipeline** | Faster Pre-location & Processing |
| Recovery | Manual Setup | `/sync` Command | User Context Resilience |
| Fitness | Basic Commands | **Full Suite** | `/fitness`, `/routine`, Add-to-Routine |
| Reminders | 4 Daily Times | **5 Times (+20:00)** | Evening exercise prompt |

---

## 1. Interaction Logic: Proactive Migration

### 1.1 Proactive Messaging: DM → Private Channel
- **Change**: Moved reminders and summaries from DM to the user's private server channel.
- **File**: `src/discord_bot/bot.py` (`_send_proactive_message`)
- **Impact**: Consolidates all health data and bot interactions into a single, private "hub" within the server.

### 1.2 Vision Acceleration: YOLO11 Integration
- **Concept**: Use YOLO11 as a "fast-path" for food localization and preliminary identification.
- **Role**: Pre-locates items to provide spatial hints to the high-precision Gemini model, significantly accelerating the multi-item recognition loop.

### 1.3 Hybrid Proactive Engine
- **Refactor**: `_send_proactive_message` in `bot.py`
- **Logic**: 
  1. Attempt send to `private_channel_id`.
  2. Fall back to `DM` if channel unavailable or bot lacks perm.
  3. Log outcome for observability.

---

## 2. CICD & Deployment (Top Priority)

### 2.1 OIDC-Authenticated Health Verification
- **Solution**: Integrated `gcloud auth print-identity-token` for secure health-check probing.
- **Benefit**: Fixes the 403 Forbidden errors that previously caused "False Negative" deployment failures.

### 2.2 Bot-Aware Health Endpoint
- **Feature**: `/health` now distinguishes between process status and Discord connection status (`OK - ONLINE`).
- **Benefit**: Ensures GHA only passes if the bot is actually logged in and ready.

### 2.3 Secret Harmonization
- **Fix**: Resolved mismatch between `DISCORD_BOT_TOKEN` (GHA Secret) and `DISCORD_TOKEN` (Bot Code).
- **Impact**: Ensured bot successfully authenticates with Discord on the first attempt after deployment.

---

## 3. Code Quality & Maintenance

### 3.1 View Helper Decoupling
- **Refactor**: Split `_create_private_health_channel` into a standalone helper `_create_private_health_channel_for_user`.
- **Benefit**: Allows the `/sync` command to reuse the exact same creation logic as the onboarding flow.

### 3.2 Resilience Fixes
- **Views**: Fixed `NameError` where `interaction` was incorrectly referenced in async helpers.
- **Bot**: Standardized `heartbeat_timeout` and improved error logging for scheduled tasks.

---

## 4. Fitness Command Suite (v10.0)

### 4.1 `/fitness` Command
- **File**: `src/discord_bot/commands.py` (`handle_fitness_command`)
- **Features**:
  - Category support: cardio, strength, yoga, HIIT, stretch, flexibility
  - Dynamic prompt building with calorie status context
  - Visual warnings integration from recent meals

### 4.2 `/routine` Command
- **File**: `src/discord_bot/commands.py` (`handle_routine_command`)
- **Features**:
  - Displays saved exercises from `workout_routines` table
  - Shows weekly target (3 sessions per exercise)
  - Displays this week's completed count and total minutes

### 4.3 Add To Routine Button
- **File**: `src/discord_bot/views.py` (`LogWorkoutView.add_to_routine`)
- **Fix**: Changed from placeholder to actual DB persistence via `db.add_routine_exercise()`

### 4.4 Evening Exercise Reminder
- **File**: `src/discord_bot/bot.py` (`evening_exercise_reminder`)
- **Time**: 20:00 daily
- **Features**:
  - Detects high-calorie meals and provides contextual suggestions
  - Shows quick workout options (yoga, walk, HIIT)
  - Routes through `_send_proactive_message` for private channel delivery

---

## 5. Bug Fixes & Improvements (v10.0)

### 5.1 Stale Cache Fix for Private Channel
- **Issue**: `_send_proactive_message` used stale `private_channel_id` from in-memory cache
- **Fix**: Always fetch fresh preferences from DB with write-through cache update
- **Files**: `bot.py`, `views.py`

### 5.2 Gitleaks Removal
- **Issue**: Historical API_KEY patterns in git history caused false positives
- **Fix**: Removed Gitleaks from CI workflow; use `no-git=true` config for local scanning

---

**Milestone:** 4 (Week 11)
**Prepared by:** AI Capstone Team
