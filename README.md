# PokeFetch

`PokeFetch` is a terminal CLI inspired by `neofetch` that shows Pokemon profile info with styled output, artwork/ASCII, and live extra data.

Repository: [tamagonocammy/pokefetch](https://github.com/tamagonocammy/pokefetch)

## Why use it

- Quick Pokemon lookup directly from your terminal
- Random Pokemon mode when no name is provided
- Shiny mode for alternate artwork
- Colored, readable output with key stats
- Best-effort live extras (description, evolution, weaknesses) when available

## Install

Requirements:

- Python `>=3.8`
- Internet connection (for live extras and remote artwork)

Clone and install:

```bash
git clone https://github.com/tamagonocammy/pokefetch.git
cd pokefetch
pip install .
```

For development:

```bash
pip install -e .
```

## Quickstart

```bash
# Random Pokemon
pokefetch

# By name
pokefetch Snorlax

# By id-like input (works if resolvable in the data set)
pokefetch 143

# Shiny mode
pokefetch Charizard --shiny

# Force iTerm2/compatible inline image protocol
pokefetch Pikachu --imgcat
```

Run from source (without installing):

```bash
PYTHONPATH=src python3 -m pokefetch.main Pikachu --shiny
```

## CLI Reference

Usage:

```text
pokefetch [name] [--shiny] [--imgcat]
```

Arguments:

- `name` (optional): Pokemon name (case-insensitive) or id key
  - Common variants are accepted (for example: `mr-mime`, `farfetchd`, `nidoran-f`, `type-null`)

Options:

- `--shiny`: Use shiny artwork
- `--imgcat`: Force iTerm2-style inline image protocol
- `-h`, `--help`: Show help

Behavior notes:

- If `name` is omitted, a random Pokemon is selected.
- Display fallback order is:
  1. `imgcat` protocol (when supported or forced)
  2. `term-image` rendering
  3. Built-in ASCII art
- Extra details are fetched from [pokemondb.net](https://pokemondb.net) on a best-effort basis.
- Cache locations:
  - Metadata cache: `~/.cache/pokefetch`
  - Downloaded images: `~/.cache/pokefetch/images`

## Troubleshooting

- `Error: Pokemon '<name>' not found.`:
  - Check spelling and try a canonical Pokemon name.
- `Warning: Could not fetch extra details (...)`:
  - This is usually a temporary network issue or source-page structure change.
  - Core output can still work using local package data.
- No inline image shown:
  - Install dependencies (`pip install -e .` or `pip install .`)
  - Try `--imgcat` in a compatible terminal
  - If image rendering is unavailable, ASCII fallback is expected

## Contributing

Contributions are welcome.

Suggested local workflow:

```bash
git clone https://github.com/tamagonocammy/pokefetch.git
cd pokefetch
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pokefetch --help
```

When opening a PR, include:

- What changed
- Why it changed
- How you tested it

## Roadmap

- Improve robustness of live-data parsing
- Add tests for argument handling and fallback rendering paths
- Improve support for special-form and edge-case Pokemon names
- Add optional offline-first mode for cached lookups

## License

MIT

## Credits

- Core Pokemon data and ASCII art from the [`pokemon`](https://pypi.org/project/pokemon/) package
- Extra scraped details from [pokemondb.net](https://pokemondb.net)
