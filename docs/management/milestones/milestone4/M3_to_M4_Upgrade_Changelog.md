# Milestone 3 → Milestone 4: Hybrid Architecture Upgrade Changelog

**Document Version:** 1.0
**Date:** 2026-03-25
**Scope:** Changes between M3 (v8.5) and M4 (v9.5)

---

## 🚀 Key Improvements

| Component | M3 State | M4 State | Impact |
|-----------|----------|----------|--------|
| deployment | Unreliable Verification | **OIDC Verified CICD** | 100% Deployment Confidence |
| Proactive | DM-hosted notifications | **Channel-hosted Proactive** | Unified User Experience |
| Recovery | Manual Setup | `/sync` Command | User Context Resilience |
| Observability | Generic "OK" signal | Bot-Connection Aware | Real-time Health Tracking |

---

## 1. Interaction Logic: Proactive Migration

### 1.1 Proactive Messaging: DM → Private Channel
- **Change**: Moved reminders and summaries from DM to the user's private server channel.
- **File**: `src/discord_bot/bot.py` (`_send_proactive_message`)
- **Impact**: Consolidates all health data and bot interactions into a single, private "hub" within the server.

### 1.2 Automated Private Channels (Enhanced)
- **Refinement**: While basic channel creation existed, M4 introduced deeper permission handling and state persistence for proactive routing.
- **File**: `src/discord_bot/views.py` (`RegistrationViewB`)

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

**Milestone:** 4 (Week 11)
**Prepared by:** AI Capstone Team
