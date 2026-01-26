import argparse
import random
import sys
import textwrap

import requests
from bs4 import BeautifulSoup
from pokemon.master import catch_em_all


def fetch_extra_data(url):
    """Fetches description and base stats from the pokemon's DB page."""
    if not url:
        return {}

    print(f"Fetching extra details from {url}...")
    try:
        response = requests.get(url, timeout=5)
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

    return details


def main():
    parser = argparse.ArgumentParser(
        description="Display pokemon info in neofetch style"
    )
    parser.add_argument("name", nargs="?", help="Name of the pokemon to search for")
    args = parser.parse_args()

    pokemons = catch_em_all()

    # Create name to ID mapping (case insensitive)
    name_to_id = {}
    for pid, data in pokemons.items():
        if "name" in data:
            name_to_id[data["name"].lower()] = pid

    target_pid = None

    if args.name:
        search_name = args.name.lower()
        if search_name in name_to_id:
            target_pid = name_to_id[search_name]
        else:
            # Try to see if it's an ID
            if search_name in pokemons:
                target_pid = search_name
            else:
                print(f"Error: Pokemon '{args.name}' not found.")
                sys.exit(1)
    else:
        target_pid = random.choice(list(pokemons.keys()))

    data = pokemons[target_pid]

    # Fetch extra data
    extra = fetch_extra_data(data.get("link"))
    data.update(extra)

    display_pokemon(data)


def display_pokemon(data):
    ascii_art = data.get("ascii", "")
    if not ascii_art:
        ascii_art = "No ASCII art available."

    ascii_lines = ascii_art.split("\n")

    # Prepare info lines
    info_lines = []

    # Colors (ANSI escape codes)
    BOLD = "\033[1m"
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    type_colors = {
        "normal": WHITE,
        "fire": RED,
        "water": BLUE,
        "grass": GREEN,
        "electric": YELLOW,
        "ice": CYAN,
        "fighting": RED,
        "poison": MAGENTA,
        "ground": YELLOW,
        "flying": CYAN,
        "psychic": MAGENTA,
        "bug": GREEN,
        "rock": YELLOW,
        "ghost": MAGENTA,
        "dragon": BLUE,
        "steel": WHITE,
        "fairy": MAGENTA,
    }

    primary_type = data.get("type", ["normal"])[0].lower()
    ascii_color = type_colors.get(primary_type, WHITE)

    # Helper for colored labels
    def label(text):
        return f"{BOLD}{ascii_color}{text}:{RESET}"

    info_lines.append(f"{ascii_color}{BOLD}{data.get('name', 'Unknown')}{RESET}")
    info_lines.append(
        f"{ascii_color}" + "-" * (len(data.get("name", "Unknown"))) + f"{RESET}"
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
            info_lines.append(f"\033[3m{line}\033[0m")  # Italic for description

    # Link
    link = data.get("link")
    if link:
        info_lines.append("")
        info_lines.append(f"\033[1mClick here for more information!\033[0m")
        info_lines.append(f"\033[4m{link}\033[0m")

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
            line_out += f"{ascii_color}{ascii_lines[i]}{RESET}"
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
