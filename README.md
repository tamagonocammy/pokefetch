# PokeFetch

A CLI tool that displays Pokémon information in a `neofetch`-style format, including ASCII art and stats.

## Installation

1.  Make sure you have Python installed.
2.  Install the required package:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the script using Python:

```bash
python3 pokefetch.py [pokemon_name_or_id]
```

### Examples

**Get a random Pokémon:**

```bash
python3 pokefetch.py
```

**Get a specific Pokémon by name:**

```bash
python3 pokefetch.py Pikachu
python3 pokefetch.py Charizard
```

**Get a specific Pokémon by ID:**

```bash
python3 pokefetch.py 150
```

## Features

*   **ASCII Art**: Displays an ASCII representation of the Pokémon.
*   **Stats**: Shows Name, ID, Type, Height, Weight, and Abilities.
*   **Color**: The output is color-coded based on the Pokémon's primary type.
