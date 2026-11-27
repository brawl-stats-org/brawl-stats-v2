from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .brawl_account import BrawlAccount


class BrawlAccountColumnar(BaseModel):
    """Columnar representation of BrawlAccount data.

    Structure (example):
    {
        "n": 1870,  # rows = days x accounts

        "dict": {
            "player": ["#Y808UYR2", "#VQ9GJGL2", ...], # tracked players
        },

        "cols": {
            "timestamp": [1234567890, 1234567920, ...],             # unix timestamp (int)
            "player": [0, 1, 2, ...],                               # index into dict.player
            "trophies": [1234, 2345, 3456, ...],                    # int
            "highest_trophies": [2345, 3456, 4567, ...],            # int
            "win_solo": [12, 34, 56, ...],                          # int
            "win_duo": [23, 45, 67, ...],                           # int
            "win_3v3": [34, 56, 78, ...],                           # int
            "prestiges": [1, 2, 3, ...],                            # int
            "brawler_count": [12, 13, 14, ...],                     # int
            "ranked_current_rank": [12, 13, 14, ...],               # int or null
            "ranked_current_elo": [1234, 2345, 3456, ...],          # int or null
            "ranked_highest_season_rank": [12, 13, 14, ...],        # int or null
            "ranked_highest_season_elo": [1234, 2345, 3456, ...],   # int or null
            "ranked_highest_OAT_rank": [12, 13, 14, ...],           # int or null
            "ranked_highest_OAT_elo": [1234, 2345, 3456, ...],      # int or null
        }
    }
    """

    n: int = 0

    # Dictionaries for encoding
    player_dict: list[str] = Field(default_factory=list)

    # Column arrays (all length = n)
    timestamp: list[int] =                              Field(default_factory=list)
    player: list[int] =                                 Field(default_factory=list)
    trophies: list[int] =                               Field(default_factory=list)
    highest_trophies: list[int] =                       Field(default_factory=list)
    win_solo: list[int] =                               Field(default_factory=list)
    win_duo: list[int] =                                Field(default_factory=list)
    win_3v3: list[int] =                                Field(default_factory=list)
    prestiges: list[int] =                              Field(default_factory=list)
    brawler_count: list[int] =                          Field(default_factory=list)
    ranked_current_rank: list[Optional[int]] =          Field(default_factory=list)
    ranked_current_elo: list[Optional[int]] =           Field(default_factory=list)
    ranked_highest_season_rank: list[Optional[int]] =   Field(default_factory=list)
    ranked_highest_season_elo: list[Optional[int]] =    Field(default_factory=list)
    ranked_highest_OAT_rank: list[Optional[int]] =      Field(default_factory=list)
    ranked_highest_OAT_elo: list[Optional[int]] =       Field(default_factory=list)

    def _get_or_add_index(self, dict_list: list[str], value: str) -> int:
        """Get index of value in dict, add if not present"""
        if value not in dict_list:
            dict_list.append(value)
        return dict_list.index(value)

    @classmethod
    def from_brawl_accounts(cls, accounts: list[BrawlAccount]) -> 'BrawlAccountColumnar':
        """Convert a list of BrawlAccount instances to columnar format"""
        result = cls()
        for account in accounts:
            player_index = result._get_or_add_index(result.player_dict, account.tag)
            result.timestamp.append(int(account.timestamp.timestamp()))
            result.player.append(player_index)
            result.trophies.append(account.trophies)
            result.highest_trophies.append(account.highest_trophies)
            result.win_solo.append(account.win_solo)
            result.win_duo.append(account.win_duo)
            result.win_3v3.append(account.win_3v3)
            result.prestiges.append(account.total_prestiges)
            result.brawler_count.append(account.brawler_count)
            result.ranked_current_rank.append(account.current_rank)
            result.ranked_current_elo.append(account.current_elo)
            result.ranked_highest_season_rank.append(account.highest_season_rank)
            result.ranked_highest_season_elo.append(account.highest_season_elo)
            result.ranked_highest_OAT_rank.append(account.highest_OAT_rank)
            result.ranked_highest_OAT_elo.append(account.highest_OAT_elo)

        result.n = len(result.timestamp)
        return result

    def add_raw_snapshot(self, snapshot_file: dict) -> None:
        """Append one row per player from a raw snapshot file (v2 storage format).

        Reads the raw API dicts directly, skipping BrawlAccount parsing. Field mapping
        and fallbacks must stay in sync with brawl_account._parse_player_data.

        Args:
            snapshot_file: v2 format {"timestamp": "...Z", "players": [raw player, ...]}

        Raises:
            ValueError: If the file is not v2 format or a player is missing required fields
        """
        if not isinstance(snapshot_file, dict) or 'players' not in snapshot_file or 'timestamp' not in snapshot_file:
            raise ValueError("Snapshot file is not v2 format (expected 'timestamp' and 'players' keys)")

        timestamp = int(datetime.fromisoformat(snapshot_file['timestamp']).timestamp())

        for raw in snapshot_file['players']:
            try:
                trophies = raw['trophies']
                brawlers = raw.get('brawlers', [])
                ranked = raw.get('ranked') or {}

                self.timestamp.append(timestamp)
                self.player.append(self._get_or_add_index(self.player_dict, raw['tag']))
                self.trophies.append(trophies)
                self.highest_trophies.append(raw.get('highestTrophies', trophies))
                self.win_solo.append(raw.get('soloVictories', 0))
                self.win_duo.append(raw.get('duoVictories', 0))
                self.win_3v3.append(raw.get('3vs3Victories', 0))
                self.prestiges.append(sum(b['trophies'] // 1000 for b in brawlers))
                self.brawler_count.append(len(brawlers))
                self.ranked_current_rank.append(ranked.get('rank'))
                self.ranked_current_elo.append(ranked.get('elo'))
                self.ranked_highest_season_rank.append(ranked.get('bestSeasonRank'))
                self.ranked_highest_season_elo.append(ranked.get('bestSeasonElo'))
                self.ranked_highest_OAT_rank.append(ranked.get('bestRank'))
                self.ranked_highest_OAT_elo.append(ranked.get('bestElo'))
            except KeyError as e:
                raise ValueError(f"Failed to parse player {raw.get('tag', 'unknown')}: missing {e}") from e

            self.n += 1

    def validate(self) -> bool:
        """Validate all column arrays have length = n"""
        expected_len = self.n
        return all(len(col) == expected_len for col in [
            self.timestamp,
            self.player,
            self.trophies,
            self.highest_trophies,
            self.win_solo,
            self.win_duo,
            self.win_3v3,
            self.prestiges,
            self.brawler_count,
            self.ranked_current_rank,
            self.ranked_current_elo,
            self.ranked_highest_season_rank,
            self.ranked_highest_season_elo,
            self.ranked_highest_OAT_rank,
            self.ranked_highest_OAT_elo
        ])

    def merge(self, other: 'BrawlAccountColumnar') -> 'BrawlAccountColumnar':
        """Merge another BrawlAccountColumnar into this one.

        Snapshots don't have duplicates (one per day per player), so just
        concatenate arrays after remapping player indices.

        Args:
            other: Another BrawlAccountColumnar to merge

        Returns:
            Self for method chaining
        """
        # Build remapping for other's player dict → self's player dict
        player_remap = [self._get_or_add_index(self.player_dict, p) for p in other.player_dict]

        # Concatenate columns, remapping player indices
        self.timestamp.extend(other.timestamp)
        self.player.extend([player_remap[idx] for idx in other.player])
        self.trophies.extend(other.trophies)
        self.highest_trophies.extend(other.highest_trophies)
        self.win_solo.extend(other.win_solo)
        self.win_duo.extend(other.win_duo)
        self.win_3v3.extend(other.win_3v3)
        self.prestiges.extend(other.prestiges)
        self.brawler_count.extend(other.brawler_count)
        self.ranked_current_rank.extend(other.ranked_current_rank)
        self.ranked_current_elo.extend(other.ranked_current_elo)
        self.ranked_highest_season_rank.extend(other.ranked_highest_season_rank)
        self.ranked_highest_season_elo.extend(other.ranked_highest_season_elo)
        self.ranked_highest_OAT_rank.extend(other.ranked_highest_OAT_rank)
        self.ranked_highest_OAT_elo.extend(other.ranked_highest_OAT_elo)

        self.n += other.n

        return self

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return self.model_dump(exclude_none=True)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string"""
        import json
        return json.dumps(self.to_dict(), indent=indent)
