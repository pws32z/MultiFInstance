# MultiFInstance

A Windows desktop tool for managing and monitoring multiple Roblox accounts simultaneously, built with Python and tkinter. Detects biomes and aura equips in real time and fires Discord webhook alerts automatically.

---

## Features

### Dashboard
Overview panel showing all active accounts, their current biome, and live activity log of recent detections and events.

### Accounts
Add and manage multiple Roblox accounts. Each account stores a Roblox username, an optional per-account Discord webhook URL, and a private server link.

### Instances
Configure individual game instances — each with its own username, private server URL, and webhook. Instances can be launched directly from the UI via Roblox deep-links (`roblox://`), bypassing the web redirect rate limit.

### Biome Actions
Set per-biome notification rules. Rare biomes (Dreamspace, Cyberspace, Singularity, Glitched, Hell, etc.) are configured to always notify and ping `@everyone` by default. Normal biome is set to never notify. All rules are customizable.

### Discord / Webhooks
Global webhook manager — add multiple webhooks and target them at all accounts or specific ones. Webhooks fire rich Discord embeds including biome name, emoji, color, thumbnail image, username, timestamp, and a private server join link when one is configured.


### Biome & Aura Detection
Reads Roblox log files in real time (supports Roblox, Bloxstrap, and Fishstrap log directories). Detects the current biome via Rich Presence hoverText and aura equips via log pattern matching. On a change, fires all applicable webhooks for that account.

---


## Requirements

- Windows 10 or 11
- Python 3.8+ (only needed if running from source)
- Roblox, Bloxstrap, or Fishstrap installed

### Python dependencies (auto-installed)
- `Pillow` — icon rendering
- `pywin32` — Windows process and GUI APIs
- `psutil` — process monitoring

---

## Running from Source

```
python MultiFInstance.py
```

## Configuration

Settings are saved automatically to `config.json` in the same directory as the executable. This includes all accounts, instances, webhook configs, and biome action rules. No manual editing required.

---

## License

GNU General Public License v3.0 — see the license text embedded in the application (accessible via the UI) for full terms.
