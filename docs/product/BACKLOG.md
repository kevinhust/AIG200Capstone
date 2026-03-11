# Product Backlog

## Priority Levels
- P0: Critical, blocks release
- P1: High, should be in next release
- P2: Medium, nice to have
- P3: Low, future consideration

---

## v7.0 Proactive Nudging (P2)

**Status**: Planned
**Estimated Effort**: 2-3 days

### Description
Transform the bot from "passive responder" to "proactive caregiver" by analyzing user habits and sending personalized reminders at optimal times.

### Core Features
1. **User Time Window Detection**
   - Analyze `workout_logs` to find high-frequency exercise time slots
   - Store preferred time windows per user (e.g., "Tuesday 20:00-21:00 Yoga")

2. **Scheduled Push System**
   - Discord Bot scheduled task (APScheduler or Celery Beat)
   - Check every hour at :00 for matching time windows

3. **Personalized Messages**
   - Template: "🧘 又是你的瑜伽时间了！今天能量充裕，正合适～"
   - Integrate with Budget Progress for context-aware messaging

4. **Feedback Loop (v7.1)**
   - Allow users to react: "太累了" / "很舒服"
   - Write feedback to `workout_logs.notes` for future habit analysis

### Technical Requirements
- `src/scheduler/` module for task scheduling
- `user_time_windows` table in Supabase
- Push notification templates in `embed_builder.py`

---

## Multi-Language Support (P3)

**Status**: Future
**Estimated Effort**: 1 week

### Description
Support English/Chinese bilingual interface based on user preference.

---

## Meal Photo Batch Upload (P3)

**Status**: Future
**Estimated Effort**: 3-4 days

### Description
Allow users to upload multiple food photos at once for batch analysis.

---

*Last Updated: 2026-03-10*
