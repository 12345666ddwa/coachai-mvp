Subject: Your CoachAI changes — reviewed, two fixes pushed, a couple of questions

Hi Alfie,

Thanks for the commits — good to see the UI polish and the multi-provider support land. I went through everything and here is where things stand.

**What I reviewed (your commit 750a71a)**
- UI adjustments in `app.py` (colours, phrasing like "Review Against Criteria", Chinese cleanup, dark-mode removal): looks fine, good direction.
- New Gemini + OpenAI providers in `agents/models.py`, plus the `.env.example`, README and test updates.

**Two things I fixed and pushed to main** (they would have broken the repo for everyone):
1. `.gradio/certificate.pem` — a locally generated Gradio TLS certificate (it contains a private key). Removed. That folder is machine-generated; it should never be committed.
2. The `coachai-mvp` file at the repo root — an accidental git submodule reference (looks like the repo was cloned inside itself). It makes every fresh clone show submodule errors. Removed.

Your `tsr_docx/` files are kept as-is (they are yours to keep in the repo). Just so you know: that's ~46 MB of NESA material in a public repo — if we ever want the repo to stay light, we can move them out and document how to fetch them. No action needed now.

**About the API key / "insufficient balance"**
- The "insufficient balance" you saw was from a DeepSeek key you tried; the project's key that Xing manages is fine and has balance. So the pipeline itself works.
- One important rule: keys must never go into the repo. `.env` is already gitignored, and each person keeps their own key locally.
- For your own runs you have two zero-cost options:
  a. **Local Ollama** — completely free, no key at all. Guide: `docs/OLLAMA_SETUP.md` (I added this yesterday).
  b. Ask Xing directly for the project key (share it privately, never in the repo or chat groups).
- On Gemini: the free tier has very tight limits, so it's better kept as an optional fallback rather than something we rely on.

**Two questions for you**
1. **Default provider.** You set `DEFAULT_PROVIDER = "openai"`, but currently none of us has an OpenAI key — so a fresh clone of the repo would fail on the very first model call. Two options:
   a. I make the default **auto-select based on which key exists in `.env`** (DeepSeek → OpenAI → Gemini → Ollama). Then everyone's environment just works.
   b. Or we set the default back to DeepSeek (the key the team actually uses).
   Which do you prefer?
2. **Deployment / video.** You mentioned you want a video showing the functionality. A full cloud deploy is possible (Vercel can't host long-running Python; the practical free option is Render), but since what you need is a demo video, the simpler path is: **we are recording a full walkthrough of all five tabs** (marking, lesson planner, students, practice & ask, lesson review) and will share the video with the team. If you'd rather record it yourself on a live instance, say so and we'll set up the Render deployment instead.

**Small git-hygiene note for future commits** (keeps everyone's clone clean):
- Never commit: `.env`, `*.pem` / certificates, `.gradio/`, locally generated files, or large binaries unless we decide they belong in the repo.
- `.gradio/` is being added to `.gitignore`.

Anything above unclear, ping me on WeChat — happy to jump on a call.

— Xing
