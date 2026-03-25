# Milestone 3 → Milestone 4: Hybrid Architecture Upgrade Changelog

**Document Version:** 1.0
**Date:** 2026-03-25
**Scope:** Changes between M3 (v8.5) and M4 (v9.5)

---

## 🚀 Key Improvements

| Component | M3 State | M4 State | Impact |
|-----------|----------|----------|--------|
| Interaction | DM Only | Hybrid Private Channels | Professional Server Presence |
| Recovery | Manual Setup | `/sync` Command | User Context Resilience |
| Deployment | 4m "False Negative" | <1m Verified Success | 4x Faster DevOps Loop |
| Resilience | Silent Connection Fail | Active Health Status | Real-time Observability |

---

## 1. Interaction Architecture: The Hybrid Transition

### 1.1 Automated Private Channels
- **Feature**: Automatic creation of dedicated logging channels upon profile completion.
- **File**: `src/discord_bot/views.py` (`RegistrationViewB`)
- **Impact**: Provides users with a persistent "Health Hub" inside the community server without compromising privacy.

### 1.2 Recovery Mechanism: `/sync` Command
- **Feature**: Re-scars/Re-creates channels if deleted or if user joined via DM.
- **File**: `src/discord_bot/bot.py`
- **Logic**: Triggered via message handler; verifies profile exists → creates channel → updates Supabase.

### 1.3 Hybrid Proactive Engine
- **Refactor**: `_send_proactive_message` in `bot.py`
- **Logic**: 
  1. Attempt send to `private_channel_id`.
  2. Fall back to `DM` if channel unavailable or bot lacks perm.
  3. Log outcome for observability.

---

## 2. DevOps & Infrastructure Resilience

### 2.1 Authenticated Health Checks (GHA)
- **Fix**: Added OIDC token authentication to the verification cycle.
- **File**: `.github/workflows/deploy-bot.yml`
- **Benefit**: Resolves 403 Forbidden errors when checking private Cloud Run services.

### 2.2 Shared Connection State
- **Refactor**: Integrated `BOT_CONNECTED` flag into `bot.py` shared with the internal health server.
- **Benefit**: Health endpoint `/health` now reports `OK - STARTING` vs `OK - ONLINE`, preventing false-positive "Ready" signals from Cloud Run before the Discord gateway is established.

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
