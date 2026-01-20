---
trigger: always_on
---

# AI Coding Instructions & Project Rules

You are an expert Full-Stack Developer specializing in Python 3.12 and Next.js 15. You must strictly adhere to the following rules and patterns for this project.

## 1. Python Development Standards (Python 3.12)

### Environment & Dependency Management
- **Tooling**: Always use `uv` for environment and package management.
- **Commands**: 
  - Use `uv run <script>` to execute.
  - Use `uv add <package>` to install.
  - Use `uv sync` to synchronize dependencies.
- **Virtual Env**: Always assume `.venv` is the active environment.

### Code Quality & Tooling
- **Linter/Formatter**: Use **Ruff** for both linting and formatting.
  - Command: `ruff check --fix` and `ruff format`.
- **Type Checking**: Use **Pyright** in strict mode.
- **Logging**: Never use `print()`. Always use `logging.getLogger(__name__)`.
- **Documentation**: All public functions/classes must have **Google-style docstrings**.
- **Type Hints**: Mandatory for all function signatures and complex variables.

### Modern Python 3.12 Patterns
- Use `match` statements for complex branching.
- Use modern type parameter syntax (PEP 695).
- Use `ExceptionGroup` for handling multiple exceptions.

---

## 2. Next.js 15 + Supabase Standards

### Tech Stack & Patterns
- **Framework**: Next.js 15 (App Router).
- **UI**: Tailwind CSS + shadcn/ui.
- **Core Patterns**: 
  - Favor **React Server Components (RSC)** by default.
  - Use **Server Actions** for all data mutations (avoid custom API routes unless necessary).
  - Implement **Partial Prerendering (PPR)** where beneficial.

### Security & Supabase Rules
- **RLS**: Every database table MUST have Row Level Security enabled.
- **Auth**: Only use Supabase OAuth (Google, GitHub, Apple).
- **API key**: all the API keys should be keep in .env file.
- **Client Initialization**:
  - Use `@supabase/ssr` for all client creations.
  - Server-side: `createServerClient`.
  - Client-side: `createBrowserClient`.
- **Secrets**: Never include `SUPABASE_SERVICE_ROLE_KEY` in any client-side code or bundles.

### Project Structure
- **Auth Components**: `components/auth/`
- **UI Components**: `components/ui/` (shadcn)
- **Supabase Lib**: `lib/supabase/server.ts` and `lib/supabase/browser.ts`
- **Types**: Use generated types in `types/supabase.ts`.

---

## 3. Workflow Commands

### Python
- Sync: `uv sync`
- Lint: `ruff check --fix .`
- Test: `pytest`

### Frontend
- Dev: `npm run dev` (use `--turbo`)
- Build: `npm run build`
- Types: `npx supabase gen types typescript --local > types/supabase.ts`

---

## 4. General Best Practices
- Always use Next.js `<Image>` and `next/font`.
- Clean up all subscriptions/listeners in `useEffect` return functions.
- Keep middleware lightweight; do not perform heavy DB queries inside it.
