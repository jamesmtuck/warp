# Troubleshooting Warp

## Run the Doctor

```bash
warp doctor
```

This checks:
- Config file existence
- Database writability
- Shell integration files
- `fzf` availability (optional)
- `git` availability
- Backend configuration

## Common Issues

### "warp: command not found"

Ensure warp is installed and in your PATH:

```bash
pip install -e .
which warp
```

### Config not initialized

```bash
warp config init
```

### Database errors

Delete the database and reinitialize:

```bash
rm ~/.local/share/warp/warp.db
warp config init
```

### Shell integration not capturing commands

1. Make sure you sourced the integration script in your shell rc file.
2. Open a new terminal session.
3. Run `warp doctor` to check shell integration.

### OpenAI backend not working

1. Set your API key: `export OPENAI_API_KEY=sk-...`
2. Or add it to config: `openai_api_key = "sk-..."` in `~/.config/warp/config.toml`
3. Install the openai package: `pip install 'warp[openai]'`

### fzf not available (interactive selection falls back to numbered menu)

Install fzf:
- macOS: `brew install fzf`
- Ubuntu/Debian: `apt install fzf`
- From source: https://github.com/junegunn/fzf#installation

### Commands not appearing in search results

- Wait for capture to complete (it runs in the background).
- Verify with `warp search "partial command"`.
- Check that the command isn't in the ignored prefixes list.

## Debug Mode

```bash
# Show config
warp config show

# Test capture manually
warp capture "ls -la" --exit-code 0 --shell bash --cwd /tmp --session-id test

# Search to verify
warp search "ls"
```
