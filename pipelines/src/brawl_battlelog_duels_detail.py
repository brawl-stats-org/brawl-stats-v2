from pydantic import BaseModel, Field
from typing import Optional
from src import BattleLog, BattleLogEntry


class BattleLogDuelsDetail(BaseModel):
    """Per-brawler detail for duels battles.

    Extends battlelog_core by splitting duels concatenated brawlers into individual rows
    with per-brawler trophy changes and stats. Use battle_time + player to join back to core.

    Structure (example):
    {
        "n": 1380,  # ~460 duels battles x 3 brawlers per player

        "dict": {
            "player": ["#2L0U0PGRL", "#JJ8P8URQC", ...],  # tracked players
            "brawler": ["SHELLY", "COLT", "BULL", ...],   # individual brawlers (not concatenated)
        },

        "cols": {
            "battle_time": [1234567890, 1234567890, 1234567890, ...],  # unix timestamp (join key)
            "player": [0, 0, 0, 1, 1, 1, ...],                         # index into dict.player
            "brawler": [12, 8, 23, ...],                               # index into dict.brawler
            "brawler_position": [0, 1, 2, 0, 1, 2, ...],              # 0=first, 1=second, 2=third
            "trophy_change": [5, 5, 5, -7, -7, -7, ...],              # per-brawler TC (not summed)
            "power": [11, 10, 11, ...],                                # brawler power level
            "trophies": [1250, 800, 1100, ...],                        # brawler trophies before battle
        }
    }

    Note: Only contains duels battles. Filter core by mode="duels" to find corresponding rows.
    """
    n: int = 0

    # Dictionaries for encoding
    player_dict: list[str] =  Field(default_factory=list)
    brawler_dict: list[str] = Field(default_factory=list)

    # Column arrays (all length = n)
    battle_time: list[int] =             Field(default_factory=list)
    player: list[int] =                  Field(default_factory=list)
    brawler: list[int] =                 Field(default_factory=list)
    brawler_position: list[int] =        Field(default_factory=list)
    trophy_change: list[Optional[int]] = Field(default_factory=list)
    power: list[int] =                   Field(default_factory=list)
    trophies: list[int] =                Field(default_factory=list)

    def validate(self) -> bool:
        """Validate that all column arrays have length = n"""
        expected_len = self.n
        column_arrays = [
            self.battle_time,
            self.player,
            self.brawler,
            self.brawler_position,
            self.trophy_change,
            self.power,
            self.trophies,
        ]
        return all(len(col) == expected_len for col in column_arrays)

    def _get_or_add_index(self, dict_list: list[str], value: str) -> int:
        """Get index of value in dict, add if not present"""
        if value not in dict_list:
            dict_list.append(value)
        return dict_list.index(value)

    def add_duels_battle_entry(self, entry: BattleLogEntry, tracked_tags: set[str]) -> None:
        """Add rows for all tracked players' brawlers in this duels battle.

        Args:
            entry: BattleLogEntry with mode="duels"
            tracked_tags: Set of player tags to include
        """
        if entry.mode != "duels":
            return  # Only process duels battles

        tracked_tags = {tag.upper() for tag in tracked_tags}  # Normalize to uppercase
        players = entry.get_all_players()
        for player in players:
            if player.tag.upper() not in tracked_tags:
                continue  # Skip untracked players
            for i, brawler in enumerate(player.brawlers):
                self.battle_time.append(int(entry.battle_time.timestamp()))
                self.player.append(self._get_or_add_index(self.player_dict, player.tag))
                self.brawler.append(self._get_or_add_index(self.brawler_dict, brawler.name))
                self.brawler_position.append(i) # dunno if order is garanteed, but assume first=0, second=1, third=2
                self.trophy_change.append(brawler.trophy_change)
                self.power.append(brawler.power)
                self.trophies.append(brawler.trophies)

    @classmethod
    def from_battlelog(cls, battlelog: BattleLog, tracked_tags: set[str]) -> 'BattleLogDuelsDetail':
        """Extract duels battles from BattleLog and convert to columnar detail format.

        Args:
            battlelog: Full BattleLog (will filter for mode="duels")
            tracked_tags: Set of player tags to include

        Returns:
            BattleLogDuelsDetail with expanded brawler rows
        """
        result = cls()
        for entry in battlelog.entries:
            result.add_duels_battle_entry(entry, tracked_tags)
        result.n = len(result.battle_time)
        return result

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return self.model_dump(exclude_none=True)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string"""
        import json
        return json.dumps(self.to_dict(), indent=indent)
