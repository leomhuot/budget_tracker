# Project Summary - May 25, 2026

## Major Enhancements & Fixes

### 1. Goal Savings Visibility
- Updated `index.html` to include a dynamic "Savings Goal" selection field.
- The field automatically appears when the "Expense" type and "Goal Savings" category are selected.

### 2. Email System Upgrade (Brevo Web API)
- Switched from SMTP to **Brevo Web API (HTTP)** to bypass Render's outbound SMTP port blocks (25, 465, 587).
- Implemented `send_brevo_email` helper function in `app.py`.
- Updated password reset and admin registration notifications to use this new API.
- **Required Render Variables**: `MAIL_PASSWORD` (Brevo API Key) and `MAIL_DEFAULT_SENDER`.

### 3. Database & Performance Optimization
- Consolidated multiple `CREATE TABLE` statements in `db.py` into a single SQL execution.
- This reduces network round-trips to the Supabase server (Singapore), preventing Render boot timeouts ("No open ports detected").

### 4. Income Category Editing Fix
- Resolved a bug where income transactions were restricted to a hardcoded "Payroll" category during editing.
- Passed `income_categories` from settings to `edit.html` and removed the hardcoded fallback.

### 5. Report Filter Enhancements
- Changed the default report period from "Monthly" to **"Daily"**.
- Implemented **Session Persistence**: The app now remembers the last selected report period (e.g., Weekly, Yearly, Custom) even after navigating away from the page.

## Maintenance Notes
- **Brevo Account**: Free plan (300 emails/day), does not expire.
- **2FA**: TOTP-based authentication remains independent and functional.
- **Deployment**: Always use "Clear Build Cache & Deploy" on Render if startup issues occur.
