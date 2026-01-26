# Project Context: PokeFetch

This document provides a technical overview of the **PokeFetch** project, a CLI tool generated to display Pokémon statistics and ASCII art in a visual style reminiscent of `neofetch`.

## Project Overview

*   **Goal**: Display ASCII art and metadata for a specific or random Pokémon.
*   **Language**: Python 3
*   **Dependencies**: `pokemon` (PyPI package), `requests`, `beautifulsoup4`

## Codebase Structure

### `pokefetch.py`
The main executable script.
*   **Imports**: `argparse`, `random`, `sys`, `textwrap`, `requests`, `bs4`, and `pokemon.master`.
*   **Logic**:
    1.  Initializes `argparse` to accept an optional Pokémon name or ID.
    2.  Fetches all Pokémon data using `catch_em_all()`.
    3.  Resolves the target Pokémon (by name case-insensitive, by ID, or random).
    4.  **`fetch_extra_data(url)`**:
        *   Scrapes `pokemondb.net` using `requests` and `BeautifulSoup`.
        *   Extracts the Pokedex entry description and Base Stats (HP, Atk, Def, etc.).
    5.  **`display_pokemon(data)`**:
        *   Extracts metadata (Name, ID, Type, Height, Weight, Abilities, Stats, Description).
        *   Determines ANSI color codes based on the Pokémon's primary type.
        *   Splits ASCII art into lines.
        *   Iterates through lines to print ASCII art and Info side-by-side with dynamic padding.

### `requirements.txt`
Contains the project dependencies.
*   `pokemon`: The library used for fetching Pokémon data and ASCII art.
*   `requests`: Used for HTTP requests to fetch online data.
*   `beautifulsoup4`: Used for parsing HTML content.

## Features & Implementation Details

*   **Type-Based Coloring**: The script uses a dictionary `type_colors` to map Pokémon types (like 'fire', 'grass') to specific ANSI escape codes, coloring the ASCII art and text headers accordingly.
*   **Live Data Integration**: Connects to `pokemondb.net` to retrieve up-to-date descriptions and base stats that aren't available in the local database.
*   **Layout Engine**: Custom logic calculates the maximum width of the ASCII art to ensure the textual information block is perfectly aligned to the right, regardless of the art's shape.
*   **Error Handling**: Gracefully handles missing Pokémon names by printing an error and exiting. Fails gracefully if web fetching encounters errors.

## Usage Guide

```bash
# Setup
pip install -r requirements.txt

# Run (Random)
python3 pokefetch.py

# Run (Specific)
python3 pokefetch.py Snorlax
python3 pokefetch.py 143
```