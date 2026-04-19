import argparse
import base64
import hashlib
import json
import os
import random
import re
import sys
import textwrap
from datetime import date
from typing import Any, Dict, List, Optional
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

CACHE_SCHEMA_VERSION = "2"
STAT_NAMES = ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]
SPECIAL_ALIAS_OVERRIDES = {
    "nidoranf": "nidoranfemale",
    "nidoranm": "nidoranmale",
}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _normalize_gender_token(token: str) -> str:
    if token in {"f", "female"}:
        return "female"
    if token in {"m", "male"}:
        return "male"
    return token


def _compact_lookup_key(value: Optional[str]) -> str:
    if not value:
        return ""

    lowered = value.lower()
    lowered = lowered.replace("♀", " female ").replace("♂", " male ")
    lowered = lowered.replace("’", "").replace("'", "")
    lowered = re.sub(r"[-_./:]", " ", lowered)
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    tokens = [_normalize_gender_token(token) for token in lowered.split()]
    return "".join(tokens)


def _slug_from_url(url: Optional[str]) -> str:
    if not url:
        return ""
    return url.rstrip("/").split("/")[-1].lower()


def _build_alias_index(pokemons: Dict[str, Any]) -> Dict[str, str]:
    alias_index: Dict[str, str] = {}
    for pid, data in pokemons.items():
        name = data.get("name")
        if name:
            alias_index[_compact_lookup_key(name)] = pid

        slug = _slug_from_url(data.get("link"))
        if slug:
            alias_index[_compact_lookup_key(slug)] = pid
    return alias_index


def _cache_key_payload(url: str, is_shiny: bool) -> str:
    return f"v{CACHE_SCHEMA_VERSION}|{url}|shiny={is_shiny}"


def _build_cache_key(url: str, is_shiny: bool = False) -> str:
    return hashlib.md5(_cache_key_payload(url, is_shiny).encode("utf-8")).hexdigest()


def _load_cached_data(cache_path: str) -> Dict[str, Any]:
    if not os.path.exists(cache_path):
        return {}

    try:
        with open(cache_path, "r") as f:
            cached_data = json.load(f)
        if isinstance(cached_data, dict) and cached_data:
            return cached_data
    except (IOError, json.JSONDecodeError):
        return {}
    return {}


def _find_header(soup: BeautifulSoup, candidates: List[str]):
    wanted = {candidate.lower() for candidate in candidates}
    for header in soup.find_all(["h2", "h3"]):
        header_text = _normalize_text(header.get_text(" ", strip=True)).lower()
        if header_text in wanted:
            return header
    return None


def _extract_description(soup: BeautifulSoup) -> Optional[str]:
    header = _find_header(soup, ["Pokédex entries", "Pokedex entries"])
    if not header:
        return None

    for table in header.find_all_next("table", class_="vitals-table", limit=2):
        cell = table.find("td", class_="cell-med-text")
        if cell:
            text = _normalize_text(cell.get_text(" ", strip=True))
            if text:
                return text
    return None


def _extract_genus(soup: BeautifulSoup) -> Optional[str]:
    for table in soup.find_all("table", class_="vitals-table"):
        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = _normalize_text(th.get_text(" ", strip=True)).lower()
            if label in {"species", "genus"}:
                genus = _normalize_text(td.get_text(" ", strip=True))
                if genus:
                    return genus
    return None


def _normalize_image_url(src: str) -> str:
    if src.startswith("//"):
        return f"https:{src}"
    if src.startswith("/"):
        return f"https://pokemondb.net{src}"
    return src


def _extract_image_url(soup: BeautifulSoup, url: str, is_shiny: bool) -> Optional[str]:
    if is_shiny:
        shiny_matches = []
        for img in soup.find_all("img"):
            src = (img.get("src") or img.get("data-src") or "").strip()
            if src and "sprites/home/shiny" in src:
                shiny_matches.append(_normalize_image_url(src))
        if shiny_matches:
            return shiny_matches[0]
        slug = _slug_from_url(url)
        if slug:
            return f"https://img.pokemondb.net/sprites/home/shiny/{slug}.png"
        return None

    artwork_priorities = ("official-artwork", "artwork", "sprites/home/normal")
    for priority in artwork_priorities:
        for img in soup.find_all("img"):
            src = (img.get("src") or img.get("data-src") or "").strip()
            if src and priority in src:
                return _normalize_image_url(src)
    return None


def _extract_stats(soup: BeautifulSoup) -> Dict[str, str]:
    header = _find_header(soup, ["Base stats", "Base Stats"])
    if not header:
        return {}

    table = header.find_next("table", class_="vitals-table")
    if not table:
        return {}

    stats: Dict[str, str] = {}
    for row in table.find_all("tr"):
        stat_header = row.find("th")
        stat_value = row.find("td", class_="cell-num") or row.find("td")
        if not stat_header or not stat_value:
            continue
        stat_name = _normalize_text(stat_header.get_text(" ", strip=True))
        if stat_name in STAT_NAMES:
            value_text = _normalize_text(stat_value.get_text(" ", strip=True))
            if value_text and any(char.isdigit() for char in value_text):
                stats[stat_name] = value_text
    return stats


def _extract_evolution(soup: BeautifulSoup) -> List[str]:
    header = _find_header(soup, ["Evolution chart", "Evolution chain"])
    container = None
    if header:
        container = header.find_next("div", class_="evolution-profile")
        if not container:
            container = header.find_next("div", class_="infocard-list-evo")
    if not container:
        container = soup.find("div", class_="evolution-profile")
    if not container:
        container = soup.find("div", class_="infocard-list-evo")
    if not container:
        return []

    names: List[str] = []
    seen = set()
    for node in container.find_all("a"):
        node_name = _normalize_text(node.get_text(" ", strip=True))
        if not node_name:
            continue
        href = node.get("href", "")
        if "/pokedex/" not in href and "ent-name" not in (node.get("class") or []):
            continue
        if node_name not in seen:
            names.append(node_name)
            seen.add(node_name)
    return names


def _parse_multiplier(value: str) -> Optional[float]:
    value = value.strip()
    mapping = {"4": 4.0, "2": 2.0, "1": 1.0, "0": 0.0, "½": 0.5, "¼": 0.25}
    if value in mapping:
        return mapping[value]
    if "/" in value:
        parts = value.split("/", 1)
        if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
            denominator = float(parts[1].strip())
            if denominator != 0:
                return float(parts[0].strip()) / denominator
    try:
        return float(value)
    except ValueError:
        return None


def _extract_weaknesses(soup: BeautifulSoup) -> List[str]:
    header = _find_header(soup, ["Type defenses", "Type Defenses", "Type effectiveness"])
    if not header:
        return []

    table = header.find_next("table")
    if not table:
        return []

    header_cells = table.find_all("th")
    raw_headers: List[str] = []
    for cell in header_cells:
        text = _normalize_text(cell.get_text(" ", strip=True))
        if text and len(text) <= 10:
            raw_headers.append(text)

    data_row = None
    for row in table.find_all("tr"):
        tds = row.find_all("td")
        if tds and any(_normalize_text(td.get_text(" ", strip=True)) for td in tds):
            data_row = tds
            break

    if not raw_headers or not data_row:
        return []

    width = min(len(raw_headers), len(data_row))
    weaknesses: List[str] = []
    for idx in range(width):
        multiplier = _parse_multiplier(_normalize_text(data_row[idx].get_text(" ", strip=True)))
        if multiplier is not None and multiplier > 1:
            weaknesses.append(raw_headers[idx][:3].title())

    return weaknesses


def parse_extra_data_from_html(html: Any, url: str, is_shiny: bool = False) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    details: Dict[str, Any] = {}
    description = _extract_description(soup)
    genus = _extract_genus(soup)
    image_url = _extract_image_url(soup, url, is_shiny)
    stats = _extract_stats(soup)
    evolution = _extract_evolution(soup)
    weaknesses = _extract_weaknesses(soup)

    if description:
        details["description"] = description
    if genus:
        details["genus"] = genus
    if image_url:
        details["image_url"] = image_url
    if stats:
        details["stats"] = stats
    if evolution:
        details["evolution"] = evolution
    if weaknesses:
        details["weaknesses"] = weaknesses

    return details


def fetch_extra_data(url: str, is_shiny: bool = False) -> Dict[str, Any]:
    """Fetches description, stats, evolution, and type defenses from the pokemon's DB page."""
    if not url:
        return {}

    # Check local cache
    cache_dir = os.path.expanduser("~/.cache/pokefetch")
    os.makedirs(cache_dir, exist_ok=True)
    # Include is_shiny in cache key so we cache shiny/normal separately
    cache_key = _build_cache_key(url, is_shiny)
    cache_path = os.path.join(cache_dir, f"{cache_key}.json")

    cached_data = _load_cached_data(cache_path)
    if cached_data:
        return cached_data

    try:
        headers = {"User-Agent": "pokefetch-cli/1.0"}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
    except Exception as e:
        print(f"Warning: Could not fetch extra details ({e})")
        return {}

    details = parse_extra_data_from_html(response.content, url=url, is_shiny=is_shiny)

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

    search_key = name_or_id.lower()
    if search_key in pokemons:
        return search_key

    # Create name to ID mapping (case insensitive)
    name_to_id = {}
    for pid, data in pokemons.items():
        if "name" in data:
            name_to_id[data["name"].lower()] = pid

    if search_key in name_to_id:
        return name_to_id[search_key]

    alias_index = _build_alias_index(pokemons)
    compact_key = _compact_lookup_key(name_or_id)
    compact_key = SPECIAL_ALIAS_OVERRIDES.get(compact_key, compact_key)
    if compact_key in alias_index:
        return alias_index[compact_key]
        
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Display pokemon info in neofetch style"
    )
    parser.add_argument("name", nargs="?", help="Name of the pokemon to search for")
    parser.add_argument("--imgcat", action="store_true", help="Force usage of iTerm2 inline image protocol")
    parser.add_argument("--shiny", action="store_true", help="Show shiny version")
    parser.add_argument("--today", action="store_true", help="Show today's Pokémon (same pick all day)")
    args = parser.parse_args()

    pokemons = catch_em_all()

    if args.today and not args.name:
        random.seed(date.today().toordinal())
        target_pid = resolve_pokemon_id(None, pokemons)
        random.seed()
    else:
        target_pid = resolve_pokemon_id(args.name, pokemons)

    if not target_pid:
        print(f"Error: Pokemon '{args.name}' not found.")
        sys.exit(1)
        
    data = pokemons[target_pid]

    # Fetch extra data
    extra = fetch_extra_data(data.get("link"), is_shiny=args.shiny)
    data.update(extra)
    data["shiny"] = args.shiny

    display_pokemon(data, force_imgcat=args.imgcat)


def print_imgcat(image_path: str, width: int = 35, height: int = 20) -> bool:
    """Displays image using iTerm2 inline image protocol. Returns True if successful."""
    try:
        with open(image_path, "rb") as f:
            data = f.read()

        encoded = base64.b64encode(data).decode("ascii")
        size = len(data)
        name = base64.b64encode(os.path.basename(image_path).encode("utf-8")).decode("ascii")

        osc = f"\033]1337;File=name={name};inline=1;size={size};width={width};height={height};preserveAspectRatio=1:{encoded}\a"

        if os.environ.get("TMUX"):
            # Wrap in tmux DCS passthrough; each ESC inside the payload must be doubled
            payload = osc.replace("\033", "\033\033")
            seq = f"\033Ptmux;{payload}\033\\"
        else:
            seq = osc

        sys.stdout.write(seq)
        sys.stdout.flush()
        return True
    except Exception:
        return False


def print_kitty(image_path: str, cols: int = 35, rows: int = 20) -> bool:
    """Displays image using Kitty graphics protocol (supported by Ghostty). Returns True if successful."""
    try:
        with open(image_path, "rb") as f:
            data = f.read()

        encoded = base64.b64encode(data).decode("ascii")
        chunk_size = 4096
        chunks = [encoded[i:i + chunk_size] for i in range(0, len(encoded), chunk_size)]

        if not chunks:
            return False

        def _apc(payload: str) -> str:
            return f"\033_{payload}\033\\"

        if len(chunks) == 1:
            sys.stdout.write(_apc(f"a=T,f=100,t=d,m=0,c={cols},r={rows};{chunks[0]}"))
        else:
            sys.stdout.write(_apc(f"a=T,f=100,t=d,m=1,c={cols},r={rows};{chunks[0]}"))
            for chunk in chunks[1:-1]:
                sys.stdout.write(_apc(f"m=1;{chunk}"))
            sys.stdout.write(_apc(f"m=0;{chunks[-1]}"))

        sys.stdout.flush()
        return True
    except Exception:
        return False


def _format_stat_bar(stat_label: str, value: int, color: str, max_val: int = 255, bar_width: int = 18) -> str:
    filled = max(0, min(bar_width, round(value / max_val * bar_width)))
    bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
    return f"{COLORS['BOLD']}{color}{stat_label:<4}{COLORS['RESET']} {color}{bar}{COLORS['RESET']} {value:>3}"


def display_pokemon(data: Dict[str, Any], force_imgcat: bool = False):
    img_name = data.get("name", "unknown")
    if data.get("shiny"):
        img_name += "-shiny"
    
    image_path = download_image(data.get("image_url"), img_name)
    
    art_lines = []
    used_imgcat = False
    imgcat_width = 35
    imgcat_height = 20

    term_program = os.environ.get("TERM_PROGRAM", "")
    lc_terminal = os.environ.get("LC_TERMINAL", "")
    in_tmux = bool(os.environ.get("TMUX"))
    is_ghostty = term_program == "ghostty" or bool(os.environ.get("GHOSTTY_RESOURCES_DIR"))
    is_iterm = force_imgcat or in_tmux or term_program in ["iTerm.app", "WezTerm", "vscode"] or lc_terminal == "iTerm2" or "imgcat" in sys.argv

    # Ghostty: Kitty graphics protocol
    if image_path and is_ghostty:
        if print_kitty(image_path, cols=imgcat_width, rows=imgcat_height):
            used_imgcat = True

    # iTerm2 / WezTerm / tmux passthrough: OSC 1337
    if image_path and not used_imgcat and is_iterm:
        if print_imgcat(image_path, width=imgcat_width, height=imgcat_height):
            used_imgcat = True

    # Try term-image if imgcat was not used and library is available
    if not used_imgcat and IMAGE_LIB_AVAILABLE and image_path:
        try:
            image = from_file(image_path)
            image.height = imgcat_height
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

    # Name Header
    name_display = data.get('name', 'Unknown')
    genus = data.get('genus')
    
    if genus:
        header_text = f"{name_display}, the {genus}"
    else:
        header_text = name_display
    
    if data.get("shiny"):
        header_text = f"\u2728 {header_text}"
    
    info_lines.append(f"{ascii_color}{COLORS['BOLD']}{header_text}{COLORS['RESET']}")
    info_lines.append(
        f"{ascii_color}" + "-" * (len(header_text)) + f"{COLORS['RESET']}"
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
    
    # Weaknesses
    weaknesses = data.get("weaknesses", [])
    if weaknesses:
        # Wrap if too long
        w_str = ", ".join(weaknesses)
        if len(w_str) > 40:
             w_str = w_str[:37] + "..."
        info_lines.append(f"{label('Weakness')} {w_str}")
    
    # Evolution
    evo = data.get("evolution", [])
    if evo:
        # Simple arrow representation
        evo_str = " -> ".join(evo)
        # Check length
        if len(evo_str) > 50:
             # Try to split or truncate? Just truncate for CLI safety
             evo_str = textwrap.shorten(evo_str, width=50, placeholder="...")
        info_lines.append(f"{label('Evo')} {evo_str}")

    # Stats
    stats = data.get("stats", {})
    if stats:
        info_lines.append("")
        stat_rows = [
            ("HP",   stats.get("HP")),
            ("Atk",  stats.get("Attack")),
            ("Def",  stats.get("Defense")),
            ("SpA",  stats.get("Sp. Atk")),
            ("SpD",  stats.get("Sp. Def")),
            ("Spd",  stats.get("Speed")),
        ]
        for slabel, sval in stat_rows:
            if sval is not None:
                try:
                    info_lines.append(_format_stat_bar(slabel, int(sval), ascii_color))
                except (ValueError, TypeError):
                    pass

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
