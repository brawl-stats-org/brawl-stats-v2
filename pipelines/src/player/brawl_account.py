from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class GadgetList(BaseModel):
    gadget1: Optional[str] = None
    gadget2: Optional[str] = None

class StarPowerList(BaseModel):
    star_power1: Optional[str] = None
    star_power2: Optional[str] = None

class HyperchargeList(BaseModel):
    hypercharge: Optional[str] = None

class BuffieList(BaseModel):
    gadget_buffie: Optional[bool] = None  # None = false, True = owned
    star_power_buffie: Optional[bool] = None
    hypercharge_buffie: Optional[bool] = None

class GearList(BaseModel):
    speed_gear: Optional[bool] = None  # None = false, True = owned
    health_gear: Optional[bool] = None
    force_gear: Optional[bool] = None
    vision_gear: Optional[bool] = None
    shield_gear: Optional[bool] = None
    cooldown_gear: Optional[bool] = None
    others: Optional[list[str]] = None

class Brawler(BaseModel):
    """Individual brawler information"""
    name: str
    power: int = Field(ge=1, le=11)
    trophies: int = Field(ge=0)
    highest_trophies: int = Field(ge=0)
    gadgets: GadgetList
    star_powers: StarPowerList
    hypercharges: HyperchargeList
    buffies: BuffieList
    gears: GearList

    @property
    def prestige(self) -> int:
        """Calculate the prestige level of the brawler based on its trophies"""
        return self.trophies // 1000

class BrawlAccount(BaseModel):
    """Brawl Stars account information"""
    timestamp: datetime

    tag: str
    name: str
    name_color: Optional[str] = None # in game hex code for name color, e.g. 0xffa8e132 TODO: load into a metadata file

    trophies: int = Field(ge=0)
    highest_trophies: int = Field(ge=0)

    win_solo: int = Field(ge=0)
    win_duo: int = Field(ge=0)
    win_3v3: int = Field(ge=0)

    club_tag: Optional[str] = None
    club_name: Optional[str] = None

    brawlers: list[Brawler] = []

    # ranked stuff
    current_rank: Optional[int] = None
    current_elo: Optional[int] = None
    highest_season_rank: Optional[int] = None
    highest_season_elo: Optional[int] = None
    highest_OAT_rank: Optional[int] = None
    highest_OAT_elo: Optional[int] = None

    @classmethod
    def from_api(cls, raw: dict) -> 'BrawlAccount':
        """Create BrawlAccount from raw API response.

        Args:
            raw: Raw response from GET /players/{tag} API endpoint

        Returns:
            New BrawlAccount instance

        Raises:
            ValueError: If player data is malformed or missing required fields
        """
        try:
            return _parse_player_data(raw)
        except Exception as e:
            raise ValueError(f"Failed to parse player data: {e}") from e

    @classmethod
    def from_raw_snapshot_v1(cls, snapshot_file: dict) -> list['BrawlAccount']:
        """Create BrawlAccount list from raw snapshot file (v1 storage format).

        Args:
            snapshot_file: Snapshot file with 'clubs' and 'individual_players' keys

        Returns:
            List of BrawlAccount instances (all players in snapshot)

        Raises:
            ValueError: If snapshot data is malformed or missing required fields
        """
        accounts = []

        # Extract players from clubs
        for club in snapshot_file.get('clubs', []):
            for player_data in club.get('members', []):
                try:
                    account = _parse_player_data(player_data)
                    # Use player's timestamp from snapshot
                    if 'timestamp' in player_data:
                        account.timestamp = datetime.fromisoformat(player_data['timestamp'])
                    accounts.append(account)
                except Exception as e:
                    raise ValueError(f"Failed to parse player {player_data.get('tag', 'unknown')}: {e}") from e

        # Extract individual players
        for player_data in snapshot_file.get('individual_players', []):
            try:
                account = _parse_player_data(player_data)
                if 'timestamp' in player_data:
                    account.timestamp = datetime.fromisoformat(player_data['timestamp'])
                accounts.append(account)
            except Exception as e:
                raise ValueError(f"Failed to parse player {player_data.get('tag', 'unknown')}: {e}") from e

        return accounts

    @classmethod
    def from_raw_snapshot(cls, snapshot_file: dict | list) -> list['BrawlAccount']:
        """Create BrawlAccount list from raw snapshot file (v2 storage format).

        Args:
            snapshot_file: v2 format {"timestamp": "...", "players": [...]} OR
                          legacy list format [player_data, ...]

        Returns:
            List of BrawlAccount instances (all players in snapshot)

        Raises:
            ValueError: If snapshot data is malformed or missing required fields
        """
        accounts = []

        # Handle v2 format with top-level timestamp
        if isinstance(snapshot_file, dict) and 'players' in snapshot_file:
            timestamp_str = snapshot_file.get('timestamp')
            timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else None
            players = snapshot_file['players']
        else:
            # Legacy list format (no timestamp)
            timestamp = None
            players = snapshot_file

        for player_data in players:
            try:
                account = _parse_player_data(player_data)
                # Use top-level timestamp if available, otherwise check per-player (legacy), else datetime.now()
                if timestamp:
                    account.timestamp = timestamp
                elif 'timestamp' in player_data:
                    account.timestamp = datetime.fromisoformat(player_data['timestamp'])
                # else: keep datetime.now() from _parse_player_data
                accounts.append(account)
            except Exception as e:
                raise ValueError(f"Failed to parse player {player_data.get('tag', 'unknown')}: {e}") from e

        return accounts

    @classmethod
    def from_stored(cls, data: dict) -> 'BrawlAccount':
        """Load BrawlAccount from stored format (output of to_dict()).

        Args:
            data: Dictionary from BrawlAccount.to_dict()

        Returns:
            New BrawlAccount instance
        """
        # Handle datetime deserialization
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

    @property
    def total_victories(self) -> int:
        """Total wins across all modes"""
        return self.win_3v3 + self.win_solo + self.win_duo

    @property
    def brawler_count(self) -> int:
        """Number of brawlers unlocked"""
        return len(self.brawlers)

    @property
    def total_prestiges(self) -> int:
        """Total prestige levels across all brawlers"""
        return sum(brawler.prestige for brawler in self.brawlers)

    def to_dict(self) -> dict:
        """Serialize to dictionary, excluding None and empty dicts"""
        data = self.model_dump(exclude_none=True)
        # Remove empty nested dicts from brawlers
        for brawler in data.get('brawlers', []):
            for key in ['gears', 'buffies', 'gadgets', 'star_powers', 'hypercharges']:
                if key in brawler and not brawler[key]:
                    del brawler[key]
        return data

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string"""
        import json
        data = self.to_dict()
        # Convert datetime to ISO string
        if 'timestamp' in data and isinstance(data['timestamp'], datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return json.dumps(data, indent=indent)


# Parsing helper for player data transformation

def _parse_player_data(raw: dict) -> BrawlAccount:
    """Parse raw player API response to BrawlAccount model."""
    # Extract club info if present
    club = raw.get('club', {})
    club_tag = club.get('tag') if club else None
    club_name = club.get('name') if club else None

    # Transform brawlers
    brawlers = []
    for b in raw.get('brawlers', []):
        # Extract gadgets (up to 2)
        gadgets_raw = b.get('gadgets', [])
        gadget_list = GadgetList(
            gadget1=gadgets_raw[0]['name'] if len(gadgets_raw) > 0 else None,
            gadget2=gadgets_raw[1]['name'] if len(gadgets_raw) > 1 else None,
        )

        # Extract star powers (up to 2)
        star_powers_raw = b.get('starPowers', [])
        star_power_list = StarPowerList(
            star_power1=star_powers_raw[0]['name'] if len(star_powers_raw) > 0 else None,
            star_power2=star_powers_raw[1]['name'] if len(star_powers_raw) > 1 else None,
        )

        # Extract hypercharge (up to 1)
        hypercharges_raw = b.get('hyperCharges', [])
        hypercharge_list = HyperchargeList(
            hypercharge=hypercharges_raw[0]['name'] if len(hypercharges_raw) > 0 else None,
        )

        # Extract buffies
        buffies_raw = b.get('buffies', {})
        buffie_list = BuffieList(
            gadget_buffie=True if buffies_raw.get('gadget') else None,
            star_power_buffie=True if buffies_raw.get('starPower') else None,
            hypercharge_buffie=True if buffies_raw.get('hyperCharge') else None,
        )

        # Extract gears (6 base types + others)
        gears_raw = b.get('gears', [])
        gear_names = {g['name'] for g in gears_raw}
        base_gears = {'SPEED', 'HEALTH', 'DAMAGE', 'VISION', 'SHIELD', 'GADGET COOLDOWN'}
        other_gears = [name for name in gear_names if name not in base_gears]

        gear_list = GearList(
            speed_gear=True if 'SPEED' in gear_names else None,
            health_gear=True if 'HEALTH' in gear_names else None,
            force_gear=True if 'DAMAGE' in gear_names else None,
            vision_gear=True if 'VISION' in gear_names else None,
            shield_gear=True if 'SHIELD' in gear_names else None,
            cooldown_gear=True if 'GADGET COOLDOWN' in gear_names else None,
            others=other_gears if other_gears else None,
        )

        brawler = Brawler(
            name=b['name'],
            power=b['power'],
            trophies=b['trophies'],
            highest_trophies=b.get('highestTrophies', b['trophies']),  # Fallback to current trophies if missing
            gadgets=gadget_list,
            star_powers=star_power_list,
            hypercharges=hypercharge_list,
            buffies=buffie_list,
            gears=gear_list,
        )
        brawlers.append(brawler)

    # Extract ranked data if present
    ranked = raw.get('ranked', {})

    return BrawlAccount(
        timestamp=datetime.now(),
        tag=raw['tag'],
        name=raw['name'],
        name_color=raw.get('nameColor'),
        trophies=raw['trophies'],
        highest_trophies=raw.get('highestTrophies', raw['trophies']),  # Fallback to current trophies
        win_solo=raw.get('soloVictories', 0),
        win_duo=raw.get('duoVictories', 0),
        win_3v3=raw.get('3vs3Victories', 0),
        club_tag=club_tag,
        club_name=club_name,
        brawlers=brawlers,
        current_rank=ranked.get('rank') if ranked else None,
        current_elo=ranked.get('elo') if ranked else None,
        highest_season_rank=ranked.get('bestSeasonRank') if ranked else None,
        highest_season_elo=ranked.get('bestSeasonElo') if ranked else None,
        highest_OAT_rank=ranked.get('bestRank') if ranked else None,
        highest_OAT_elo=ranked.get('bestElo') if ranked else None,
    )