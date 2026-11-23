# PitchIQ — Next Steps (from Section 12 feedback)

Deadlines: **Section 14 peer presentation — Dec 3** · **Final submission (FP Journal 6) — Dec 7**

Source: Section 12 peer critique with Nathanal Berkman, the MCP activity, and
Journal 3 mentor notes (Aadity Sharma).

---

## 1. Accounts with Supabase

Today the pitcher profile is saved to a local JSON file
(`pitchiq/profile_store.py` → `data/profile/`), so there is only one user.
Supabase replaces that with real accounts.

- [ ] Create a Supabase project; add `supabase` to `requirements.txt`
- [ ] Keep the project URL + anon key in `.streamlit/secrets.toml` (gitignored) — never commit them
- [ ] Add sign-up / log-in / log-out (Supabase Auth, email + password)
- [ ] Create a `profiles` table (user id, name, throwing hand, arsenal, notes) with Row Level Security so each user only sees their own data
- [ ] Change `load_profile` / `save_profile` to read/write that table for the logged-in user (keep the local JSON as a fallback for offline dev)
- [ ] Move uploaded reports to Supabase Storage (private bucket per user) — reports are confidential
- [ ] Test: two different accounts can't see each other's arsenal

## 2. Hosting and a shareable link (Vercel)

**Heads up:** PitchIQ is a Streamlit app, which needs a Python server that
stays running. Vercel only runs short serverless functions and static sites,
so it can't host the Streamlit app itself. Pick one:

- **Option A (simplest):** host the Streamlit app on Streamlit Community
  Cloud (free, deploys straight from GitHub), and use Vercel for a custom
  domain / landing page that links or redirects to it.
- **Option B:** deploy the simulator (`simulator/`, a Vite + React app) to
  Vercel as its own static site, and host the Streamlit app elsewhere
  (Streamlit Community Cloud, Render, or Railway).

Tasks either way:
- [ ] Choose option A or B
- [ ] Deploy the Streamlit app; add Supabase keys as hosted secrets
- [ ] Set up the Vercel project and connect it to the GitHub repo
- [ ] Make sure Baseball Savant requests work from the hosted server (rate limits, timeouts)
- [ ] Put the final link in the README

## 3. Rearrange the app layout (Nathanal's idea)

Goal: make the **Simulator + Game Plan** the center of the app instead of a
left sidebar of five equal pages, and make it work well on phones and laptops.

- [x] Remove the **Ask PitchIQ** chat tab (no LLM API planned; matches Aadity's "program over LLM" advice)
  - remove `pitchiq/ui/chat.py` page from `app.py` and fix the footer text that mentions Claude
  - then decide whether `assistant.py`, `backends.py`, `knowledge/` and the `anthropic` / `google-genai` packages can be deleted
- [x] Try a top navigation bar instead of the sidebar (`st.navigation(pages, position="top")`, Streamlit 1.46+)
- [ ] Prototype a flow built around one opponent: pick team → game plan → simulate, instead of separate Scout / Team Matchup pages
- [ ] Explore a swipe / card layout for phones (e.g. swipe between hitters in the lineup)
- [ ] Check the layout at phone width and laptop width
- [ ] Get one or two teammates to try it and note what confuses them

## 4. Smaller fixes

- [ ] Input validation: show errors as soon as a bad value is typed (lesson from the MCP time server, where typos only showed up after pressing Enter) — e.g. hitter search, arsenal velocities
- [x] Update the README: version number, page list, remove the chatbot description
- [x] Run the tests (`pytest`, and `npm test` in `simulator/`) after removing the chat code

## 5. Section 14 presentation (Dec 3)

Slides — under 2 minutes:
- [ ] Final problem statement
- [ ] 2–3 key decisions (e.g. public MLB Statcast data instead of private MiLB data; a deterministic program instead of an LLM chatbot; the simulator driven by each hitter's real data)
- [ ] Remaining work

Demo — about 3 minutes, tied to the problem statement:
- [ ] Log in → set up My Arsenal → pick an opponent → see the game plan → simulate an at-bat
- [ ] Rehearse the whole thing to under 5 minutes total
- [ ] Write the slides myself (AI slop is graded as low quality)
