from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class BrawlerInBattle(BaseModel):
    """Brawler used in a battle"""
    name: str
    power: int = Field(ge=-1, le=11)  # API sometimes returns -1 for unknown
    trophies: int = Field(ge=-1)  # API sometimes returns -1 for unknown
    trophy_change: Optional[int] = None

class PlayerBattleLogEntry(BaseModel):
    """Individual player in a battle log entry"""
    tag: str
    name: str
    brawlers: list[BrawlerInBattle]  # len=1 normal, len=3 duels

class TeamBattleLogEntry(BaseModel):
    """Team information in a battle log entry"""
    players: list[PlayerBattleLogEntry]

    def contains_player(self, player_tag: str) -> bool:
        """Check if a player is in this team"""
        return any(player.tag.upper() == player_tag.upper() for player in self.players)

class BattleLogEntry(BaseModel):
    """Individual battle log entry information"""
    battle_time: datetime

    battle_type: str  # ranked / soloRanked / friendly / ...
    mode: str
    map: Optional[str] = None  # API sometimes returns null for map
    duration: Optional[int] = None  # None for showdown

    result: Optional[str] = None  # "victory"/"defeat" for team/duels, None for showdown

    star_player_tag: Optional[str] = None
    winning_team: Optional[TeamBattleLogEntry] = None  # winner or rank 1
    other_teams: Optional[list[TeamBattleLogEntry]] = None  # ordered by rank (showdown) or just loser (team/duels)

    def merge(self, other: 'BattleLogEntry') -> 'BattleLogEntry':
        """Merge trophy changes from another battle entry (same battle, different perspective).

        Args:
            other: Another BattleLogEntry for the same battle

        Returns:
            Self for method chaining

        Raises:
            ValueError: If battle_time doesn't match (not the same battle)
        """
        if self.battle_time != other.battle_time:
            raise ValueError(
                f"Cannot merge battles with different times: "
                f"{self.battle_time.isoformat()} != {other.battle_time.isoformat()}"
            )

        # Collect trophy changes from other
        tc_map: dict[str, int] = {}

        if other.winning_team:
            for player in other.winning_team.players:
                for brawler in player.brawlers:
                    if brawler.trophy_change is not None:
                        tc_map[player.tag] = brawler.trophy_change

        if other.other_teams:
            for team in other.other_teams:
                for player in team.players:
                    for brawler in player.brawlers:
                        if brawler.trophy_change is not None:
                            tc_map[player.tag] = brawler.trophy_change

        # Apply to self
        if self.winning_team:
            for player in self.winning_team.players:
                if player.tag in tc_map:
                    for brawler in player.brawlers:
                        brawler.trophy_change = tc_map[player.tag]

        if self.other_teams:
            for team in self.other_teams:
                for player in team.players:
                    if player.tag in tc_map:
                        for brawler in player.brawlers:
                            brawler.trophy_change = tc_map[player.tag]

        return self

    def get_all_players(self) -> list[PlayerBattleLogEntry]:
        """Return a list of all players in this battle (winning + other teams)"""
        players = []
        if self.winning_team:
            players.extend(self.winning_team.players)
        if self.other_teams:
            for team in self.other_teams:
                players.extend(team.players)
        return players

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        data = self.model_dump(exclude_none=True)
        # Convert datetime to ISO string
        if 'battle_time' in data and isinstance(data['battle_time'], datetime):
            data['battle_time'] = data['battle_time'].isoformat()
        return data

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string"""
        import json
        return json.dumps(self.to_dict(), indent=indent)


# Parsing helpers for battlelog transformation

def _parse_player(player_raw: dict, trophy_change: int = None) -> PlayerBattleLogEntry:
    """Parse a single player (standard modes)."""
    brawler_raw = player_raw['brawler']
    brawler = BrawlerInBattle(
        name=brawler_raw['name'],
        power=brawler_raw['power'],
        trophies=brawler_raw['trophies'],
        trophy_change=trophy_change,
    )

    return PlayerBattleLogEntry(
        tag=player_raw['tag'],
        name=player_raw['name'],
        brawlers=[brawler],
    )


def _parse_duels_player(player_raw: dict) -> PlayerBattleLogEntry:
    """Parse a duels player (has multiple brawlers)."""
    brawlers_raw = player_raw.get('brawlers', [])
    brawlers = []

    for b_raw in brawlers_raw:
        brawler = BrawlerInBattle(
            name=b_raw['name'],
            power=b_raw['power'],
            trophies=b_raw['trophies'],
            trophy_change=b_raw.get('trophyChange'),
        )
        brawlers.append(brawler)

    return PlayerBattleLogEntry(
        tag=player_raw['tag'],
        name=player_raw['name'],
        brawlers=brawlers,
    )


def _parse_team(team_raw: list, trophy_change: int, owner_tag: str = None, owner_tc: int = None) -> TeamBattleLogEntry:
    """Parse a team of players."""
    players = []
    for player_raw in team_raw:
        # For showdown: only owner gets trophyChange
        tc = owner_tc if owner_tag and player_raw['tag'] == owner_tag else trophy_change
        players.append(_parse_player(player_raw, tc))
    return TeamBattleLogEntry(players=players)


def _parse_team_battle(battle: dict, event: dict, battle_time: datetime, mode: str, battle_type: str, map_name: str) -> BattleLogEntry:
    """Parse standard team battle (3v3, 5v5)."""
    teams_raw = battle.get('teams', [])
    result = battle.get('result')

    # Determine winner based on result
    # teams[0] is winning team if result == "victory", else teams[1] is winner
    if result == 'victory':
        winning_idx = 0
        losing_idx = 1
    else:
        winning_idx = 1
        losing_idx = 0

    # Parse teams
    all_teams = [_parse_team(team_raw, battle.get('trophyChange', 0)) for team_raw in teams_raw]

    winning_team = all_teams[winning_idx] if len(all_teams) > winning_idx else None
    other_teams = [all_teams[losing_idx]] if len(all_teams) > losing_idx else None

    # Star player
    star_player = battle.get('starPlayer')
    star_player_tag = star_player.get('tag') if star_player else None

    return BattleLogEntry(
        battle_time=battle_time,
        battle_type=battle_type,
        mode=mode,
        map=map_name,
        duration=battle.get('duration'),
        result=result,
        star_player_tag=star_player_tag,
        winning_team=winning_team,
        other_teams=other_teams,
    )


def _parse_showdown_battle(battle: dict, event: dict, battle_time: datetime, mode: str, battle_type: str, map_name: str, owner_tag: str = None) -> BattleLogEntry:
    """Parse showdown battle (solo/duo/trio)."""
    rank = battle.get('rank')
    trophy_change = battle.get('trophyChange')

    # Showdown can have 'teams' (duo/trio) or 'players' (solo)
    if 'teams' in battle:
        # Duo/Trio showdown - teams ranked
        teams_raw = battle.get('teams', [])
        all_teams = [_parse_team(team_raw, trophy_change=None, owner_tag=owner_tag, owner_tc=trophy_change)
                     for team_raw in teams_raw]
    else:
        # Solo showdown - individual players
        players_raw = battle.get('players', [])
        all_teams = [[_parse_player(player_raw, trophy_change=trophy_change if player_raw['tag'] == owner_tag else None)]
                     for player_raw in players_raw]
        all_teams = [TeamBattleLogEntry(players=team) for team in all_teams]

    # Rank 1 is winner, rest in other_teams
    winning_team = all_teams[0] if all_teams else None
    other_teams = all_teams[1:] if len(all_teams) > 1 else None

    return BattleLogEntry(
        battle_time=battle_time,
        battle_type=battle_type,
        mode=mode,
        map=map_name,
        duration=None,  # Showdown has no duration
        result=None,  # Showdown uses rank instead
        star_player_tag=None,
        winning_team=winning_team,
        other_teams=other_teams,
    )


def _parse_duels_battle(battle: dict, event: dict, battle_time: datetime, mode: str, battle_type: str, map_name: str) -> BattleLogEntry:
    """Parse duels battle (1v1 with 3 brawlers each)."""
    players_raw = battle.get('players', [])
    result = battle.get('result')

    # Parse both players
    all_teams = [TeamBattleLogEntry(players=[_parse_duels_player(player_raw)]) for player_raw in players_raw]

    # Determine winner - in duels, typically players[0] is the queried player
    # Use result to determine which team won
    if result == 'victory':
        winning_team = all_teams[0] if len(all_teams) > 0 else None
        other_teams = [all_teams[1]] if len(all_teams) > 1 else None
    else:
        winning_team = all_teams[1] if len(all_teams) > 1 else None
        other_teams = [all_teams[0]] if len(all_teams) > 0 else None

    return BattleLogEntry(
        battle_time=battle_time,
        battle_type=battle_type,
        mode=mode,
        map=map_name,
        duration=battle.get('duration'),
        result=result,
        star_player_tag=None,  # Duels has no star player
        winning_team=winning_team,
        other_teams=other_teams,
    )


def _parse_battle_item(item: dict, owner_tag: str = None) -> BattleLogEntry:
    """Parse a single battle item from the API response."""
    battle = item['battle']
    event = item['event']

    # Parse battle time
    battle_time = datetime.strptime(item['battleTime'], "%Y%m%dT%H%M%S.%fZ")

    # Common fields
    mode = battle['mode']
    battle_type = battle.get('type', 'unknown')
    map_name = event.get('map')

    # Mode-specific parsing
    if 'rank' in battle:
        # Showdown modes (solo/duo/trio)
        return _parse_showdown_battle(battle, event, battle_time, mode, battle_type, map_name, owner_tag)
    elif mode == 'duels':
        # Duels mode
        return _parse_duels_battle(battle, event, battle_time, mode, battle_type, map_name)
    else:
        # Team modes (3v3, 5v5)
        return _parse_team_battle(battle, event, battle_time, mode, battle_type, map_name)


class BattleLog(BaseModel):
    """A collection of battle log entries"""
    entries: list[BattleLogEntry] = Field(default_factory=list)

    @classmethod
    def from_api(cls, raw: list, owner_tag: str = None) -> 'BattleLog':
        """Create BattleLog from raw API response.

        Args:
            raw: Raw response from GET /players/{tag}/battlelog API endpoint (list of battle items)
            owner_tag: Player tag who owns this battlelog (for trophy change attribution)

        Returns:
            New BattleLog instance

        Raises:
            ValueError: If battle data is malformed or missing required fields
        """
        entries = []
        for idx, item in enumerate(raw):
            try:
                entry = _parse_battle_item(item, owner_tag)
                entries.append(entry)
            except Exception as e:
                raise ValueError(f"Failed to parse battle at index {idx}: {e}") from e

        return cls(entries=entries)

    @classmethod
    def from_raw_battlelog_v1(cls, raw: list, owner_tag: str = None) -> 'BattleLog':
        """Create BattleLog from raw battlelog file (v1 storage format - per-player).

        Args:
            raw: List of battle items from raw battlelog file (same structure as API)
            owner_tag: Player tag who owns this battlelog (for trophy change attribution)

        Returns:
            New BattleLog instance

        Raises:
            ValueError: If battle data is malformed or missing required fields
        """
        return cls.from_api(raw, owner_tag)

    @classmethod
    def from_raw_battlelog(cls, raw: dict) -> 'BattleLog':
        """Create BattleLog from raw battlelog file (v2 storage format - daily).

        Args:
            raw: v2 format dict {TAG: {items: [...]}, TAG2: {items: [...]}}

        Returns:
            New BattleLog instance with all players' battles merged

        Raises:
            ValueError: If battle data is malformed or missing required fields
        """
        # Merge all players' battlelogs
        all_logs = []
        for tag, player_data in raw.items():
            battlelog = cls.from_api(player_data.get("items", []), owner_tag=tag)
            all_logs.append(battlelog)

        # Merge into single battlelog
        if not all_logs:
            return cls(entries=[])

        result = all_logs[0]
        for log in all_logs[1:]:
            result.merge(log)

        return result

    @classmethod
    def from_stored(cls, data: dict) -> 'BattleLog':
        """Create BattleLog from stored JSON format.

        Args:
            data: Stored data dict with 'entries' key (output of to_dict())

        Returns:
            New BattleLog instance
        """
        entries_data = data.get('entries', [])
        entries = []
        for entry_dict in entries_data:
            # Parse datetime from ISO string if needed
            if 'battle_time' in entry_dict and isinstance(entry_dict['battle_time'], str):
                entry_dict['battle_time'] = datetime.fromisoformat(entry_dict['battle_time'])
            entries.append(BattleLogEntry(**entry_dict))
        return cls(entries=entries)

    @classmethod
    def from_entries(cls, entries: list[BattleLogEntry]) -> 'BattleLog':
        """Create BattleLog from list of BattleLogEntry objects.

        Args:
            entries: List of BattleLogEntry objects

        Returns:
            New BattleLog instance
        """
        return cls(entries=entries)

    def merge(self, other: 'BattleLog') -> 'BattleLog':
        """Merge another BattleLog into this one, matching entries by battle_time.

        Args:
            other: Another BattleLog to merge

        Returns:
            Self for method chaining
        """
        # Create a map of battle_time to entry for quick lookup
        entry_map = {entry.battle_time: entry for entry in self.entries}

        for other_entry in other.entries:
            if other_entry.battle_time in entry_map:
                # Merge trophy changes if the battle already exists
                entry_map[other_entry.battle_time].merge(other_entry)
            else:
                # Add new battle entry
                self.entries.append(other_entry)
                entry_map[other_entry.battle_time] = other_entry

        return self

    def most_recent(self, n: int = 1) -> list[BattleLogEntry]:
        """Return the most recent n battle log entries, sorted by battle_time descending.

        Args:
            n: Number of recent entries to return

        Returns:
            List of BattleLogEntry objects
        """
        return sorted(self.entries, key=lambda e: e.battle_time, reverse=True)[:n]

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {"entries": [entry.to_dict() for entry in self.entries]}

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string"""
        import json
        return json.dumps(self.to_dict(), indent=indent)
