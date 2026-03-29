from pathlib import Path

import requests

from pokefetch import main

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class DummyResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def _pokemon_catalog():
    return {
        "29": {"name": "Nidoran♀", "link": "http://pokemondb.net/pokedex/nidoran-f"},
        "32": {"name": "Nidoran♂", "link": "http://pokemondb.net/pokedex/nidoran-m"},
        "83": {"name": "Farfetch'd", "link": "http://pokemondb.net/pokedex/farfetchd"},
        "122": {"name": "Mr. Mime", "link": "http://pokemondb.net/pokedex/mr-mime"},
        "772": {"name": "Type: Null", "link": "http://pokemondb.net/pokedex/type-null"},
        "785": {"name": "Tapu Koko", "link": "http://pokemondb.net/pokedex/tapu-koko"},
        "984": {"name": "Great Tusk", "link": "http://pokemondb.net/pokedex/great-tusk"},
    }


def test_resolve_pokemon_id_matches_special_name_variants():
    pokemons = _pokemon_catalog()

    cases = {
        "mr-mime": "122",
        "mr mime": "122",
        "farfetchd": "83",
        "nidoran-f": "29",
        "nidoran-m": "32",
        "type-null": "772",
        "great-tusk": "984",
        "tapu-koko": "785",
        "NIDORAN FEMALE": "29",
        "nidoran male": "32",
    }

    for name, expected_pid in cases.items():
        assert main.resolve_pokemon_id(name, pokemons) == expected_pid


def test_resolve_pokemon_id_preserves_priority_and_unknown(monkeypatch):
    pokemons = _pokemon_catalog()

    assert main.resolve_pokemon_id("122", pokemons) == "122"
    assert main.resolve_pokemon_id("Mr. Mime", pokemons) == "122"
    assert main.resolve_pokemon_id("totally-unknown", pokemons) is None

    monkeypatch.setattr(main.random, "choice", lambda values: "83")
    assert main.resolve_pokemon_id(None, pokemons) == "83"


def test_parse_extra_data_from_full_fixture():
    html = _read_fixture("pikachu_full.html")

    parsed = main.parse_extra_data_from_html(
        html,
        url="https://pokemondb.net/pokedex/pikachu",
        is_shiny=False,
    )

    assert parsed["description"].startswith("When several of these")
    assert parsed["genus"] == "Mouse Pokémon"
    assert parsed["image_url"].endswith("/artwork/large/pikachu.jpg")
    assert parsed["stats"]["HP"] == "35"
    assert parsed["evolution"] == ["Pichu", "Pikachu", "Raichu"]
    assert parsed["weaknesses"] == ["Gro"]


def test_parse_extra_data_from_partial_fixture_uses_fallback_selectors():
    html = _read_fixture("pikachu_partial.html")

    parsed = main.parse_extra_data_from_html(
        html,
        url="https://pokemondb.net/pokedex/pikachu",
        is_shiny=True,
    )

    assert parsed["description"].startswith("Pikachu can generate")
    assert parsed["genus"] == "Mouse Pokemon"
    assert parsed["image_url"].endswith("/sprites/home/shiny/pikachu.png")
    assert parsed["evolution"] == ["Pikachu", "Raichu"]
    assert parsed["weaknesses"] == ["Gro"]
    assert "stats" not in parsed


def test_cache_key_changes_when_schema_version_changes(monkeypatch):
    url = "https://pokemondb.net/pokedex/pikachu"

    current_key = main._build_cache_key(url, is_shiny=False)
    monkeypatch.setattr(main, "CACHE_SCHEMA_VERSION", "999")
    bumped_key = main._build_cache_key(url, is_shiny=False)

    assert current_key != bumped_key


def test_fetch_extra_data_handles_network_failure(monkeypatch):
    def raising_get(*args, **kwargs):
        raise requests.RequestException("boom")

    monkeypatch.setattr(main.requests, "get", raising_get)

    assert main.fetch_extra_data("https://pokemondb.net/pokedex/pikachu") == {}


def test_fetch_extra_data_uses_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    html = _read_fixture("pikachu_full.html")
    calls = {"count": 0}

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        return DummyResponse(html.encode("utf-8"))

    monkeypatch.setattr(main.requests, "get", fake_get)

    first = main.fetch_extra_data("https://pokemondb.net/pokedex/pikachu", is_shiny=False)
    second = main.fetch_extra_data("https://pokemondb.net/pokedex/pikachu", is_shiny=False)

    assert first == second
    assert calls["count"] == 1
