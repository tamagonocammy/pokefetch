import argparse
import hashlib
import json
import os
import random
import sys
import textwrap
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup
from pokemon.master import catch_em_all


# ANSI escape codes for styling
COLORS = {
    "BOLD": "\033[1m",
    "ITALIC": "\033[3m",
    "UNDERLINE": "\033[4m",
    "RESET": "\033[0m",
    "RED": "\033[31m",
    "GREEN": "\033[32m",
    "YELLOW": "\033[33m",
    "BLUE": "\033[34m",
    "MAGENTA": "\033[35m",
    "CYAN": "\033[36m",
    "WHITE": "\033[37m",
}

TYPE_COLORS = {
    "normal": COLORS["WHITE"],
    "fire": COLORS["RED"],
    "water": COLORS["BLUE"],
    "grass": COLORS["GREEN"],
    "electric": COLORS["YELLOW"],
    "ice": COLORS["CYAN"],
    "fighting": COLORS["RED"],
    "poison": COLORS["MAGENTA"],
    "ground": COLORS["YELLOW"],
    "flying": COLORS["CYAN"],
    "psychic": COLORS["MAGENTA"],
    "bug": COLORS["GREEN"],
    "rock": COLORS["YELLOW"],
    "ghost": COLORS["MAGENTA"],
    "dragon": COLORS["BLUE"],
    "steel": COLORS["WHITE"],
    "fairy": COLORS["MAGENTA"],
}


def fetch_extra_data(url: str) -> Dict[str, Any]:
    """Fetches description and base stats from the pokemon's DB page."""
    if not url:
        return {}

    # Check local cache
    cache_dir = os.path.expanduser("~/.cache/pokefetch")
    os.makedirs(cache_dir, exist_ok=True)
    cache_key = hashlib.md5(url.encode("utf-8")).hexdigest()
    cache_path = os.path.join(cache_dir, f"{cache_key}.json")

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            pass  # Ignore corrupt cache

    print(f"Fetching extra details from {url}...")
    try:
        # Add User-Agent to avoid being blocked by some servers
        headers = {"User-Agent": "pokefetch-cli/1.0"}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
    except Exception as e:
        # Fail silently or just print a small warning so we don't crash the whole app
        print(f"Warning: Could not fetch extra details ({e})")
        return {}

    soup = BeautifulSoup(response.content, "html.parser")
    details = {}

    # Description
    # Look for 'Pokédex entries' header
    pokedex_header = soup.find("h2", string="Pokédex entries")
    if pokedex_header:
        table = pokedex_header.find_next("table", class_="vitals-table")
        if table:
            cell = table.find("td", class_="cell-med-text")
            if cell:
                details["description"] = cell.get_text(strip=True)

    # Base Stats
    stats_header = soup.find("h2", string="Base stats")
    if stats_header:
        table = stats_header.find_next("table", class_="vitals-table")
        if table:
            rows = table.find_all("tr")
            stats = {}
            for row in rows:
                header = row.find("th")
                value = row.find("td", class_="cell-num")
                if header and value:
                    stat_name = header.get_text(strip=True)
                    if stat_name in [
                        "HP",
                        "Attack",
                        "Defense",
                        "Sp. Atk",
                        "Sp. Def",
                        "Speed",
                    ]:
                        stats[stat_name] = value.get_text(strip=True)
            details["stats"] = stats

    # Save to cache if we successfully got data
    if details:
        try:
            with open(cache_path, "w") as f:
                json.dump(details, f)
        except IOError:
            pass

    return details


def resolve_pokemon_id(name_or_id: Optional[str], pokemons: Dict[str, Any]) -> Optional[str]:
    """Resolves the pokemon ID from a name or ID string."""
    if not name_or_id:
        return random.choice(list(pokemons.keys()))
    
    # Create name to ID mapping (case insensitive)
    name_to_id = {}
    for pid, data in pokemons.items():
        if "name" in data:
            name_to_id[data["name"].lower()] = pid

    search_key = name_or_id.lower()
    if search_key in name_to_id:
        return name_to_id[search_key]
    
    if search_key in pokemons:
        return search_key
        
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Display pokemon info in neofetch style"
    )
    parser.add_argument("name", nargs="?", help="Name of the pokemon to search for")
    args = parser.parse_args()

    pokemons = catch_em_all()
    target_pid = resolve_pokemon_id(args.name, pokemons)

    if not target_pid:
        print(f"Error: Pokemon '{args.name}' not found.")
        sys.exit(1)
        
    data = pokemons[target_pid]

    # Fetch extra data
    extra = fetch_extra_data(data.get("link"))
    data.update(extra)

    display_pokemon(data)


def display_pokemon(data: Dict[str, Any]):
    ascii_art = data.get("ascii", "")
    if not ascii_art:
        ascii_art = "No ASCII art available."

    ascii_lines = ascii_art.split("\n")

    # Prepare info lines
    info_lines = []

    primary_type = data.get("type", ["normal"])[0].lower()
    ascii_color = TYPE_COLORS.get(primary_type, COLORS["WHITE"])

    # Helper for colored labels
    def label(text):
        return f"{COLORS['BOLD']}{ascii_color}{text}:{COLORS['RESET']}"

    info_lines.append(f"{ascii_color}{COLORS['BOLD']}{data.get('name', 'Unknown')}{COLORS['RESET']}")
    info_lines.append(
        f"{ascii_color}" + "-" * (len(data.get("name", "Unknown"))) + f"{COLORS['RESET']}"
    )
    info_lines.append(f"{label('ID')} {data.get('id', 'Unknown')}")

    types_list = [t.title() for t in data.get("type", [])]
    types = ", ".join(types_list)
    info_lines.append(f"{label('Type')} {types}")

    info_lines.append(f"{label('Height')} {data.get('height', '?')} m")
    info_lines.append(f"{label('Weight')} {data.get('weight', '?')} kg")

    abilities_list = [a.title() for a in data.get("abilities", [])]
    abilities = ", ".join(abilities_list)
    info_lines.append(f"{label('Abilities')} {abilities}")

    # Stats
    stats = data.get("stats", {})
    if stats:
        info_lines.append("")
        info_lines.append(
            f"{label('HP')} {stats.get('HP', '?')}  {label('Speed')} {stats.get('Speed', '?')}"
        )
        info_lines.append(
            f"{label('Atk')} {stats.get('Attack', '?')}  {label('Def')} {stats.get('Defense', '?')}"
        )
        info_lines.append(
            f"{label('SpA')} {stats.get('Sp. Atk', '?')}  {label('SpD')} {stats.get('Sp. Def', '?')}"
        )

    # Description
    desc = data.get("description")
    if desc:
        info_lines.append("")
        # Wrap description to a reasonable width (e.g., 40 chars)
        wrapper = textwrap.TextWrapper(width=50)
        wrapped_desc = wrapper.wrap(desc)
        for line in wrapped_desc:
            info_lines.append(f"{COLORS['ITALIC']}{line}{COLORS['RESET']}")

    # Link
    link = data.get("link")
    if link:
        info_lines.append("")
        info_lines.append(f"{COLORS['BOLD']}Click here for more information!{COLORS['RESET']}")
        info_lines.append(f"{COLORS['UNDERLINE']}{link}{COLORS['RESET']}")

    # Calculate padding based on max ascii width
    max_ascii_width = 0
    for line in ascii_lines:
        if len(line) > max_ascii_width:
            max_ascii_width = len(line)

    # Add some padding between art and text
    padding = 4

    # Combine
    total_lines = max(len(ascii_lines), len(info_lines))

    print()  # Top margin

    for i in range(total_lines):
        line_out = ""

        # ASCII part
        if i < len(ascii_lines):
            line_out += f"{ascii_color}{ascii_lines[i]}{COLORS['RESET']}"
            current_width = len(ascii_lines[i])
        else:
            current_width = 0

        # Spacing
        line_out += " " * (max_ascii_width - current_width + padding)

        # Info part
        if i < len(info_lines):
            line_out += info_lines[i]

        print(line_out)

    print()  # Bottom margin


if __name__ == "__main__":
    main()
