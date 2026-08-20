# llm_skills

Personal agent skills for AI coding assistants — focused on Grocy meal planning and recipe discovery.

## Installation

Install on any supported agent (Claude Code, Cursor, Windsurf, OpenCode, and 70+ others):

```bash
npx skills@latest add serhovskyi/llm_skills
```

Or, for manual linking to Claude Code and compatible harnesses:

```bash
git clone https://github.com/serhovskyi/llm_skills ~/.llm_skills
bash ~/.llm_skills/scripts/link-skills.sh
```

## Skills

### `plan-meal`

Adds products and recipes to a [Grocy](https://grocy.info) meal plan via the `grocy-nutrients` MCP server.

**Triggers:** "додай X в меню", "заплануй на завтра", "add X to my meal plan", "plan Y for tomorrow"

**Requires:** `grocy-nutrients` MCP server configured in your agent.

### `recipe-from-stock`

Suggests what to cook from your current Grocy pantry, prioritising items expiring soon. Returns 2 local Grocy recipes + 3 fresh internet recipes.

**Triggers:** "що приготувати", "знайди рецепт по залишках", "what can I cook", "recipe from my stock"

**Requires:** `grocy-nutrients` MCP server configured in your agent.

## MCP Server Setup

Both skills require the `grocy-nutrients` MCP server. Add it to your Claude Code config (`~/.claude/claude_desktop_config.json` or `settings.json`):

```json
{
  "mcpServers": {
    "grocy-nutrients": {
      "command": "npx",
      "args": ["grocy-nutrients-mcp"],
      "env": {
        "GROCY_URL": "http://your-grocy-nutrient-instance",
        "GROCY_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Structure

```
skills/
└── grocy/
    ├── plan-meal/
    │   └── SKILL.md
    └── recipe-from-stock/
        └── SKILL.md
```

## Updating a skill

**Recommended setup:** clone this repo to a permanent location and run `link-skills.sh`
once. After that, `~/.claude/skills/<name>` becomes a symlink into this repo — editing
the skill file in place *is* editing the repo. Publishing is a single command.

```bash
# One-time setup
git clone git@github.com:serhovskyi/llm_skills.git ~/llm_skills
bash ~/llm_skills/scripts/link-skills.sh
```

Now `~/.claude/skills/plan-meal/SKILL.md` points directly into `~/llm_skills/skills/grocy/plan-meal/SKILL.md`.
Edit it however you like, then publish:

```bash
bash ~/llm_skills/scripts/publish.sh "update plan-meal: clarify unit handling"
```

That's it — no copying, no separate commit step.

---

**Without the symlink setup** (e.g. you installed via `npx skills@latest add`), copy and push manually:

```bash
cp ~/.claude/skills/plan-meal/SKILL.md ~/llm_skills/skills/grocy/plan-meal/SKILL.md
bash ~/llm_skills/scripts/publish.sh "update plan-meal"
```

Users who installed via `npx skills@latest add` can pull the latest version by re-running
the same install command. Users who cloned manually just need `git pull` — the symlinks
already point into the cloned directory, so no relinking is needed.

### Adding a new skill

1. Write the skill locally at `~/.claude/skills/<skill-name>/SKILL.md`. Make sure it
   starts with the required frontmatter:
   ```yaml
   ---
   name: skill-name
   description: One-line description of when and why to invoke this skill.
   ---
   ```
2. Copy it into the repo (or just create it there directly if you used the symlink setup):
   ```bash
   mkdir -p ~/llm_skills/skills/<category>/<skill-name>
   cp ~/.claude/skills/<skill-name>/SKILL.md ~/llm_skills/skills/<category>/<skill-name>/SKILL.md
   ```
3. Publish:
   ```bash
   bash ~/llm_skills/scripts/publish.sh "add <skill-name> skill"
   ```

The `skills` CLI discovers any `SKILL.md` found under `skills/` automatically — no
registration step needed.
