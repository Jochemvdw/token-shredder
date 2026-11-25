# Token Shredder Skill for Claude Code

## Installation

```bash
claude install-skill your-org/token-shredder
```

## Triggers

- "shred this file"
- "convert to markdown"
- "minimize tokens"
- "compress file"

## Commands

- `convert FILE [--detail-level 1-5]`
- `analyze FILE`
- `batch DIR`

## Usage

```
User: "Shred this PDF and feed it to Claude"
Claude Code: Executes /shred document.pdf --detail-level 3
Output: Markdown + token report
```

## Manifest

```json
{
  "name": "Token Shredder",
  "version": "0.1.0",
  "description": "Convert files to markdown, convert files to markdown",
  "icon": "🪨",
  "triggers": ["shred", "convert", "minimize tokens"],
  "capabilities": ["file_processing", "analysis"]
}
```
