import argparse
import base64
import hashlib
import json
import os
import random
import sys
import textwrap
from typing import Any, Dict, Optional
import shutil
import warnings

# Suppress term-image warning about non-interactive terminal
warnings.filterwarnings("ignore", message="It seems this process is not running within a terminal")

import requests
from bs4 import BeautifulSoup
from pokemon.master import catch_em_all

try:
    from term_image.image import from_file
    from term_image.exceptions import TermImageError
    IMAGE_LIB_AVAILABLE = True
except ImportError:
    IMAGE_LIB_AVAILABLE = False
    # Warning will be printed later if fallback also fails


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
                cached_data = json.load(f)
                # Only use cache if it has the image_url, otherwise try fetching again
                if "image_url" in cached_data:
                    return cached_data
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
    
    # Image
    # Look for the main artwork
    # Usually <a href=".../artwork/name.jpg"> or <img src=".../artwork/name.jpg">
    # We prefer the one in the generic container if possible, but artwork is key.
    images = soup.find_all("img")
    for img in images:
        src = img.get("src", "")
        if "artwork" in src:
            details["image_url"] = src
            break

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


def download_image(url: str, name: str) -> Optional[str]:
    """Downloads the image and returns the local path."""
    if not url:
        return None
    
    cache_dir = os.path.expanduser("~/.cache/pokefetch/images")
    os.makedirs(cache_dir, exist_ok=True)
    
    ext = os.path.splitext(url)[1]
    if not ext:
        ext = ".jpg"
        
    filename = f"{name.lower()}{ext}"
    local_path = os.path.join(cache_dir, filename)
    
    if os.path.exists(local_path):
        return local_path
        
    try:
        headers = {"User-Agent": "pokefetch-cli/1.0"}
        response = requests.get(url, headers=headers, stream=True, timeout=5)
        response.raise_for_status()
        with open(local_path, "wb") as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        return local_path
    except Exception as e:
        print(f"Warning: Could not download image ({e})")
        return None


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
    parser.add_argument("--imgcat", action="store_true", help="Force usage of iTerm2 inline image protocol")
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

    display_pokemon(data, force_imgcat=args.imgcat)


def print_imgcat(image_path: str, width: int = 35, height: int = 20) -> bool:
    """Displays image using iTerm2 inline image protocol. Returns True if successful."""
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        
        encoded = base64.b64encode(data).decode("ascii")
        size = len(data)
        name = base64.b64encode(os.path.basename(image_path).encode("utf-8")).decode("ascii")
        
        # OSC 1337 ; File = [args] : Content ST
        # ST is usually BEL (\a) or ESC \
        print(
            f"\033]1337;File=name={name};inline=1;size={size};width={width};height={height};preserveAspectRatio=1:{encoded}\a",
            end=""
        )
        return True
    except Exception:
        return False


def display_pokemon(data: Dict[str, Any], force_imgcat: bool = False):
    image_path = download_image(data.get("image_url"), data.get("name", "unknown"))
    
    art_lines = []
    used_imgcat = False
    imgcat_width = 35
    imgcat_height = 20

    # Check for iTerm2 or WezTerm via environment variable
    term_program = os.environ.get("TERM_PROGRAM", "")
    lc_terminal = os.environ.get("LC_TERMINAL", "")
    is_iterm = force_imgcat or term_program in ["iTerm.app", "WezTerm", "vscode"] or lc_terminal == "iTerm2" or "imgcat" in sys.argv

    # Try imgcat first if in a supported terminal
    if image_path and is_iterm:
         # We rely on our internal implementation
         if print_imgcat(image_path, width=imgcat_width, height=imgcat_height):
             used_imgcat = True

    # Try term-image if imgcat was not used and library is available
    if not used_imgcat and IMAGE_LIB_AVAILABLE and image_path:
        try:
            image = from_file(image_path)
            # Set a reasonable height
            image.height = imgcat_height
            # Render to string
            art_str = str(image)
            art_lines = art_str.split("\n")
        except (TermImageError, Exception):
            pass

    # Fallback to ASCII if no image displayed
    if not art_lines and not used_imgcat:
        ascii_art = data.get("ascii", "")
        if not ascii_art:
            ascii_art = "No ASCII art available."
        art_lines = ascii_art.split("\n")
        
        if not IMAGE_LIB_AVAILABLE and image_path:
             print("Warning: 'term-image' library not found and 'imgcat' not supported. Falling back to ASCII art.", file=sys.stderr)
             print("To enable image display, install requirements: pip install -r requirements.txt", file=sys.stderr)

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
        # Wrap description to a reasonable width
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

    print()  # Top margin

    if used_imgcat:
        # Move cursor up to align text with image
        # We printed the image which took 'imgcat_height' lines effectively (visually)
        # But wait, the imgcat escape code prints ONCE and the cursor is at the bottom right of the image?
        # Usually it puts the cursor on the next line after the image.
        # So we need to move UP by the image height to start printing text next to it.
        print(f"\033[{imgcat_height}A", end="")
        
        # Padding to skip the image width
        # We need to use cursor movement, not spaces, to avoid overwriting the image
        # imgcat_width is in cells.
        padding_cmd = f"\033[{imgcat_width + 4}C"
        
        for line in info_lines:
            print(f"{padding_cmd}{line}")
            
        # If info lines are fewer than image height, we need to move down to clear the image area
        if len(info_lines) < imgcat_height:
            diff = imgcat_height - len(info_lines)
            print("\n" * diff, end="")
            
        print() # Final newline

    else:
        # Standard ASCII / Block render loop
        max_art_width = 0
        is_image = bool(IMAGE_LIB_AVAILABLE and image_path and art_lines and art_lines[0].startswith("\033"))
        
        if not is_image:
             for line in art_lines:
                if len(line) > max_art_width:
                    max_art_width = len(line)
        
        # Strip ansi for width calculation if using blocks
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

        padding = 4
        total_lines = max(len(art_lines), len(info_lines))

        for i in range(total_lines):
            line_out = ""

            # Art part
            if i < len(art_lines):
                line_out += f"{ascii_color if not is_image else ''}{art_lines[i]}{COLORS['RESET'] if not is_image else ''}"
                if is_image:
                    # Best effort width calc for blocks
                    stripped = ansi_escape.sub('', art_lines[i])
                    current_width = len(stripped)
                else:
                    current_width = len(art_lines[i])
            else:
                current_width = 0

            # Spacing
            if is_image:
                 # If using blocks, we just use spaces.
                 # If width is 0 (protocol image), this might misalign, but term-image 'block' style has width.
                 line_out += " " * padding
            else:
                 line_out += " " * (max_art_width - current_width + padding)

            # Info part
            if i < len(info_lines):
                line_out += info_lines[i]

            print(line_out)

    print()  # Bottom margin


if __name__ == "__main__":
    main()
