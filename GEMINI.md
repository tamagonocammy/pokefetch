# Project Context: PokeFetch

This document provides a technical overview of the **PokeFetch** project, a CLI tool generated to display Pokémon statistics and ASCII art in a visual style reminiscent of `neofetch`.

## Project Overview

*   **Goal**: Display ASCII art, metadata, evolution chains, and type weaknesses for a specific or random Pokémon.
*   **Language**: Python 3
*   **Dependencies**: `pokemon`, `requests`, `beautifulsoup4`, `term-image`, `pillow`.

## Codebase Structure

### `src/pokefetch/main.py`
The main executable logic.
*   **Imports**: `argparse`, `random`, `sys`, `textwrap`, `requests`, `bs4`, `pokemon.master`, and `term_image`.
*   **Logic**:
    1.  Initializes `argparse` to accept an optional Pokémon name/ID and a `--shiny` flag.
    2.  Fetches all Pokémon data using `catch_em_all()`.
    3.  Resolves the target Pokémon (by name case-insensitive, by ID, or random).
    4.  **`fetch_extra_data(url, is_shiny)`**:
        *   Scrapes `pokemondb.net` using `requests` and `BeautifulSoup`.
        *   Extracts Pokedex entry, Genus (Species), Base Stats, Evolution Chain, and Type Defenses (Weaknesses).
        *   Determines the correct image URL (Artwork vs. Shiny Sprite).
        *   Uses a local JSON cache in `~/.cache/pokefetch` to avoid redundant network calls.
    5.  **`display_pokemon(data)`**:
        *   Extracts metadata (Name, ID, Type, Height, Weight, Abilities, Stats, Weaknesses, Evolution).
        *   Determines ANSI color codes based on the Pokémon's primary type.
        *   Attempts to render images using `imgcat` (iTerm2/WezTerm) or `term-image` (Block render).
        *   Falls back to ASCII art if image rendering is unavailable.

### `pyproject.toml`
The modern Python packaging configuration.
*   Defines the project as an installable package `pokefetch`.
*   Maps the `pokefetch` command to `pokefetch.main:main`.

## Features & Implementation Details

*   **Header with Genus**: Displays the Pokemon's name and its official title (e.g., "Pikachu, the Mouse Pokémon").
*   **Shiny Mode**: Fetches specific shiny sprites and adds a visual "✨" indicator in the name header.
*   **Evolution & Weakness Parsing**: Analyzes the HTML structure of the Evolution Chart and Type Defense tables to extract actionable data for the user.
*   **Multi-Engine Rendering**: Support for iTerm2/WezTerm protocol (`imgcat`), terminal block characters (`term-image`), and traditional ASCII fallback.
*   **Type-Based Coloring**: Uses a dictionary `TYPE_COLORS` to map Pokémon types to specific ANSI escape codes.

## Usage Guide

```bash
# Install via pipx (recommended for CLI tools)
pipx install .

# Update existing installation
pipx install . --force

# Or install locally
pip install .

# Run (Random)
pokefetch

# Run (Specific & Shiny)
pokefetch Charizard --shiny
pokefetch 143
```