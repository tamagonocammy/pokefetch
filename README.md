# PokeFetch

PokeFetch is a command-line interface (CLI) tool that brings your favorite Pokémon to your terminal in a style inspired by `neofetch`. It displays ASCII art alongside detailed statistics, featuring dynamic coloring based on the Pokémon's type.

## Features

- **ASCII Art**: High-quality ASCII representations of every Pokémon.
- **Detailed Stats**: Displays ID, Type, Height, Weight, Abilities, and Base Stats (HP, Attack, Defense, etc.).
- **Live Data**: Fetches up-to-date descriptions and stats from [Pokémon Database](https://pokemondb.net).
- **Type-Based Coloring**: The output is color-coded to match the Pokémon's primary type (e.g., Red for Fire, Blue for Water).
- **Responsive Layout**: Automatically adjusts padding to align text perfectly with the ASCII art.

## Installation

### Prerequisites
- Python 3.6 or higher
- Internet connection (for fetching live data)

### Setup
1.  **Clone the repository** (if applicable) or download the source.
2.  **Install dependencies**:
    It is recommended to use a virtual environment.

    ```bash
    # Create a virtual environment
    python3 -m venv venv

    # Activate the virtual environment
    # On macOS/Linux:
    source venv/bin/activate
    # On Windows:
    .\venv\Scripts\activate

    # Install requirements
    pip install -r requirements.txt
    ```

## Usage

### Basic Usage
Run the script from your terminal:

```bash
# Get a random Pokémon
python3 pokefetch.py

# Get a specific Pokémon by name
python3 pokefetch.py Snorlax

# Get a specific Pokémon by ID
python3 pokefetch.py 143
```

### Running Outside a Virtual Environment
If you prefer not to activate the virtual environment every time, you can run the script using the direct path to the python executable within the `venv` folder:

```bash
# macOS/Linux
./venv/bin/python3 pokefetch.py Pikachu

# Windows
.\venv\Scripts\python.exe pokefetch.py Pikachu
```

Alternatively, you can install the dependencies globally (not recommended for system stability) using `pip install -r requirements.txt` and then run `python3 pokefetch.py` directly.

## Configuration
The script currently supports command-line arguments. No configuration file is needed.

- `[name_or_id]`: Optional. The name (case-insensitive) or Pokedex ID of the Pokémon. If omitted, a random Pokémon is chosen.

## Project Structure

- `pokefetch.py`: The main entry point and logic script.
- `requirements.txt`: List of Python dependencies.
- `GEMINI.md`: Project documentation and context.

## Troubleshooting

- **"Pokemon not found"**: Check the spelling of the Pokémon's name.
- **"Warning: Could not fetch extra details"**: This usually means there's a network issue or the scraping logic needs an update. The script will still display basic info from the local database.

## Credits
- ASCII art and basic data provided by the `pokemon` Python package.
- Detailed stats and descriptions scraped from [pokemondb.net](https://pokemondb.net).