from pydantic import BaseModel, Field
from typing import Optional
from .brawl_battlelog import BattleLog, BattleLogEntry


class BattleLogColumnar(BaseModel):
    """Columnar representation of battle log.

    Structure (example):
    {
        "n": 23305,  # total number of battles (rows)

        "dict": {
            # Dictionary encoding - maps index → string value
            "mode": ["gemGrab", "brawlBall", "heist", ...],     # ~25 unique modes
            "map": ["Ring of Fire", "Hot Potato", ...],         # ~120 unique maps
            "battle_type": ["ranked", "friendly", ...],         # ~5 types
            "brawler": ["SHELLY", "COLT", "BULL", ...],         # ~106 brawlers
            "player": ["#2L0U0PGRL", "#JJ8P8URQC", ...],        # tracked players
        },

        "cols": {
            # All arrays have length = n (23305)
            "battle_time": [1234567890, 1234567920, ...],       # unix timestamp (int)
            "player": [0, 0, 1, 2, ...],                        # index into dict.player
            "mode": [0, 1, 0, ...],                             # index into dict.mode
            "map": [5, 12, 5, ...],                             # index into dict.map
            "battle_type": [0, 0, 1, ...],                      # index into dict.battle_type
            "brawler": [23, 45, 23, ...],                       # index into dict.brawler
            "result": [1, 0, 1, ...],                           # 0=loss, 1=win, 2=draw, null for showdown
            "trophy_change": [8, -7, 0, ...],                   # int, can be null
            "is_star_player": [0, 0, 1, ...],                   # 0 or 1 (boolean as int)
        }
    }

    One row per tracked player per battle. 3v3 with 2 tracked players = 2 rows.

    NOTE: This core artifact does NOT include teammate/opponent data (brawlers, tags, names).
    That information will be stored in a separate meta artifact for matchup/synergy analysis.
    """
    n: int = 0

    # Dictionaries for encoding
    mode_dict: list[str] =          Field(default_factory=list)
    map_dict: list[str] =           Field(default_factory=list)
    battle_type_dict: list[str] =   Field(default_factory=list)
    brawler_dict: list[str] =       Field(default_factory=list)
    player_dict: list[str] =        Field(default_factory=list)

    # Column arrays (all length = n)
    battle_time: list[int] =                Field(default_factory=list)
    player: list[int] =                     Field(default_factory=list)
    mode: list[int] =                       Field(default_factory=list)
    map: list[int] =                        Field(default_factory=list)
    battle_type: list[int] =                Field(default_factory=list)
    brawler: list[int] =                    Field(default_factory=list)
    result: list[Optional[int]] =           Field(default_factory=list)
    trophy_change: list[Optional[int]] =    Field(default_factory=list)
    is_star_player: list[int] =             Field(default_factory=list)

    def _get_or_add_index(self, dict_list: list[str], value: str) -> int:
        """Get index of value in dict, add if not present"""
        if value not in dict_list:
            dict_list.append(value)
        return dict_list.index(value)

    def validate(self) -> bool:
        """Validate that all column arrays have length = n"""
        expected_len = self.n
        column_arrays = [
            self.battle_time,
            self.player,
            self.mode,
            self.map,
            self.battle_type,
            self.brawler,
            self.result,
            self.trophy_change,
            self.is_star_player,
        ]
        return all(len(col) == expected_len for col in column_arrays)

    def merge(self, other: 'BattleLogColumnar') -> 'BattleLogColumnar':
        """Merge another BattleLogColumnar into this one.

        Remaps other's dictionary indices, deduplicates by (battle_time, player),
        and merges trophy changes for duplicates (handles multiple perspectives).

        Args:
            other: Another BattleLogColumnar to merge

        Returns:
            Self for method chaining
        """
        # Build index of existing (battle_time, player) → row_idx
        existing_battles = {}
        for i in range(self.n):
            key = (self.battle_time[i], self.player[i])
            existing_battles[key] = i

        # Build remapping for other's dict indices → self's dict indices
        mode_remap = [self._get_or_add_index(self.mode_dict, m) for m in other.mode_dict]
        map_remap = [self._get_or_add_index(self.map_dict, m) for m in other.map_dict]
        battle_type_remap = [self._get_or_add_index(self.battle_type_dict, bt) for bt in other.battle_type_dict]
        brawler_remap = [self._get_or_add_index(self.brawler_dict, b) for b in other.brawler_dict]
        player_remap = [self._get_or_add_index(self.player_dict, p) for p in other.player_dict]

        # Process each row from other
        for i in range(other.n):
            remapped_player = player_remap[other.player[i]]
            key = (other.battle_time[i], remapped_player)

            if key in existing_battles:
                # Duplicate battle - merge trophy change (overwrite strategy)
                existing_idx = existing_battles[key]
                other_tc = other.trophy_change[i]

                # If other has trophy_change, use it (overwrite), else keep existing
                if other_tc is not None:
                    self.trophy_change[existing_idx] = other_tc
                # else: keep existing (whether null or not)
            else:
                # New battle - add row
                self.battle_time.append(other.battle_time[i])
                self.player.append(remapped_player)
                self.mode.append(mode_remap[other.mode[i]])
                self.map.append(map_remap[other.map[i]])
                self.battle_type.append(battle_type_remap[other.battle_type[i]])
                self.brawler.append(brawler_remap[other.brawler[i]])
                self.result.append(other.result[i])
                self.trophy_change.append(other.trophy_change[i])
                self.is_star_player.append(other.is_star_player[i])

                # Add to index
                existing_battles[key] = self.n
                self.n += 1

        return self

    def add_battle_entry(self, entry: BattleLogEntry, tracked_tags: set[str]) -> None:
        """Add rows for all tracked players in this battle

        DUELS MODE QUIRK: Duels battles use 3 brawlers per player. These are stored
        as a single brawler entry in format: "duels|BRAWLER1|BRAWLER2|BRAWLER3"
        Trophy change is the sum of all 3 brawlers' trophy changes.
        Frontend should treat duels brawler strings as opaque IDs.
        """
        tracked_tags = {tag.upper() for tag in tracked_tags}

        players = entry.get_all_players()
        tracked_players = 0
        for player in players:
            if player.tag.upper() not in tracked_tags:
                continue  # skip untracked players

            tracked_players += 1
            self.battle_time.append(int(entry.battle_time.timestamp()))
            self.player.append(self._get_or_add_index(self.player_dict, player.tag))
            self.mode.append(self._get_or_add_index(self.mode_dict, entry.mode))
            self.map.append(self._get_or_add_index(self.map_dict, entry.map or "unknown"))
            self.battle_type.append(self._get_or_add_index(self.battle_type_dict, entry.battle_type))

            # Handle duels mode (3 brawlers) vs normal modes (1 brawler)
            if entry.mode == "duels" and len(player.brawlers) == 3:
                brawler_name = f"duels|{player.brawlers[0].name}|{player.brawlers[1].name}|{player.brawlers[2].name}"
                trophy_change = sum(b.trophy_change or 0 for b in player.brawlers)
            else:
                brawler_name = player.brawlers[0].name
                trophy_change = player.brawlers[0].trophy_change

            self.brawler.append(self._get_or_add_index(self.brawler_dict, brawler_name))

            if entry.winning_team and entry.winning_team.contains_player(player.tag):
                self.result.append(1) # win
            elif entry.other_teams and any(team.contains_player(player.tag) for team in entry.other_teams):
                self.result.append(0) # loss
            elif entry.result == "draw":
                self.result.append(2) # draw
            else:
                self.result.append(None) # null for showdown or unknown

            self.trophy_change.append(trophy_change)
            if entry.star_player_tag and entry.star_player_tag.upper() == player.tag.upper():
                self.is_star_player.append(1)
            else:
                self.is_star_player.append(0)

        self.n += tracked_players

    @classmethod
    def from_battlelog(cls, battlelog: BattleLog, tracked_tags: set[str]) -> 'BattleLogColumnar':
        """Convert BattleLog to columnar format"""
        result = cls()
        for entry in battlelog.entries:
            result.add_battle_entry(entry, tracked_tags)
        result.n = len(result.battle_time)
        return result

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return self.model_dump(exclude_none=True)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string"""
        import json
        return json.dumps(self.to_dict(), indent=indent)