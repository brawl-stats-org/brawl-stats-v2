"""modes and maps, keyed by the ids battles carry (`event.modeId`, `event.id`).

Disabled rows are kept: old battles still reference them.
"""

from brawlify.core.dump import Dump


def hex_color(argb: str | None) -> str | None:
    """`"0xff9ab1fd"` -> `"#9ab1fd"`."""
    return "#" + argb[-6:].lower() if argb else None


def build(dump: Dump) -> dict[str, list]:
    variations = dump.table("game_mode_variations")
    modes = [
        {
            "id": mode["id"],
            "modeId": mode["Variation"],
            "tid": mode["TID"],
            "disabled": mode["Disabled"],
            "color": hex_color(mode["Color"]),
            "imageUrl": dump.cdn_url("game-modes/regular", mode["id"]),
        }
        for mode in variations.values()
    ]
    maps = [
        {
            "id": location["id"],
            "tid": location["TID"],
            "modeId": variations[location["GameModeVariation"]]["Variation"],
            "disabled": location["Disabled"],
            "imageUrl": dump.cdn_url("maps/regular", location["id"]),
        }
        for location in dump.table("locations").values()
    ]
    return {"modes": modes, "maps": maps}
