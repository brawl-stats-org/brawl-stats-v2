from pydantic import BaseModel, Field
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from src.brawl_account import Brawler

# Lightweight models for memory-efficient detail generation
class GadgetListLight(BaseModel):
    gadget1: Optional[str] = None
    gadget2: Optional[str] = None

class StarPowerListLight(BaseModel):
    star_power1: Optional[str] = None
    star_power2: Optional[str] = None

class HyperchargeListLight(BaseModel):
    hypercharge: Optional[str] = None

class BuffieListLight(BaseModel):
    gadget_buffie: Optional[bool] = None
    star_power_buffie: Optional[bool] = None
    hypercharge_buffie: Optional[bool] = None

class GearListLight(BaseModel):
    speed_gear: Optional[bool] = None
    health_gear: Optional[bool] = None
    force_gear: Optional[bool] = None
    vision_gear: Optional[bool] = None
    shield_gear: Optional[bool] = None
    cooldown_gear: Optional[bool] = None
    others: Optional[list[str]] = None

class BrawlerLight(BaseModel):
    """Lightweight brawler model for detail generation (excludes highest_trophies)"""
    name: str
    power: int
    trophies: int
    gadgets: GadgetListLight
    star_powers: StarPowerListLight
    hypercharges: HyperchargeListLight
    buffies: BuffieListLight
    gears: GearListLight

class SnapshotLight(BaseModel):
    """Lightweight snapshot model for detail generation (excludes account-level stats)"""
    timestamp: datetime
    brawlers: list[BrawlerLight]

class BrawlerDetail(BaseModel):
    """Single brawler's time-series data
    
    Structure (example):
    {
        "n": 170,
        "timestamp": [...],     # unix timestamps (int)
        "trophies": [...],      # int
        "power": [...],         # int (1-11)
        "has_gadget1": [...],   # bool
        "has_gadget2": [...],   # bool
        "has_sp1": [...],       # bool
        "has_sp2": [...],       # bool
        "has_hc": [...],        # bool
        "gear_count": [...],    # bool
        "buffie_gadget": [...], # bool
        "buffie_sp": [...],     # bool
        "buffie_hc": [...]      # bool
    }
    """
    n: int = 0
    timestamp: list[int] =                  Field(default_factory=list)
    trophies: list[int] =                   Field(default_factory=list)
    power: list[int] =                      Field(default_factory=list)
    has_gadget1: list[Optional[bool]] =     Field(default_factory=list)
    has_gadget2: list[Optional[bool]] =     Field(default_factory=list)
    has_sp1: list[Optional[bool]] =         Field(default_factory=list)
    has_sp2: list[Optional[bool]] =         Field(default_factory=list)
    has_hc: list[Optional[bool]] =          Field(default_factory=list)
    gear_count: list[int] =                 Field(default_factory=list)
    buffie_gadget: list[Optional[bool]] =   Field(default_factory=list)
    buffie_sp: list[Optional[bool]] =       Field(default_factory=list)
    buffie_hc: list[Optional[bool]] =       Field(default_factory=list)

    @classmethod
    def from_brawler_snapshots(cls, timestamps: list[datetime], brawlers: list['Brawler']) -> 'BrawlerDetail':
        """Build detail from brawler snapshots"""
        result = cls()
        for brawler, timestamp in zip(brawlers, timestamps):
            result.n += 1
            result.timestamp.append(int(timestamp.timestamp()))
            result.trophies.append(brawler.trophies)
            result.power.append(brawler.power)
            result.has_gadget1.append(True if brawler.gadgets.gadget1 else None)
            result.has_gadget2.append(True if brawler.gadgets.gadget2 else None)
            result.has_sp1.append(True if brawler.star_powers.star_power1 else None)
            result.has_sp2.append(True if brawler.star_powers.star_power2 else None)
            result.has_hc.append(True if brawler.hypercharges.hypercharge else None)
            result.gear_count.append(sum([brawler.gears.speed_gear or 0,
                                          brawler.gears.health_gear or 0,
                                          brawler.gears.force_gear or 0,
                                          brawler.gears.vision_gear or 0,
                                          brawler.gears.shield_gear or 0,
                                          brawler.gears.cooldown_gear or 0,
                                          len(brawler.gears.others) if brawler.gears.others else 0]))
            result.buffie_gadget.append(True if brawler.buffies.gadget_buffie else None)
            result.buffie_sp.append(True if brawler.buffies.star_power_buffie else None)
            result.buffie_hc.append(True if brawler.buffies.hypercharge_buffie else None)
        return result

class PlayerSnapshotDetail(BaseModel):
    """Per-player brawler detail artifact
    
    Structure (example):
    {
        "player_tag": "#ABC",
        "brawlers": {
            "SHELLY": {
                "n": 170,
                "timestamp": [...],
                # ... 11 arrays
            },
            "BULL": {
                "n": 10,  # unlocked recently
                "timestamp": [...],
                # ... 11 arrays
            }
        }
    }
    """
    player_tag: str
    brawlers: dict[str, BrawlerDetail] = Field(default_factory=dict)

    @classmethod
    def from_snapshots(cls, player_tag: str, snapshots: list['BrawlAccount']) -> 'PlayerSnapshotDetail':
        """Build detail from player snapshots (BrawlAccount objects)"""
        brawler_snapshots: dict[str, tuple[list[datetime], list['Brawler']]] = {}
        for snapshot in snapshots:
            for brawler in snapshot.brawlers:
                if brawler.name not in brawler_snapshots:
                    brawler_snapshots[brawler.name] = ([], [])
                timestamps, brawlers = brawler_snapshots[brawler.name]
                timestamps.append(snapshot.timestamp)
                brawlers.append(brawler)

        result = cls(player_tag=player_tag)
        for brawler_name, (timestamps, brawlers) in brawler_snapshots.items():
            result.brawlers[brawler_name] = BrawlerDetail.from_brawler_snapshots(timestamps, brawlers)
        return result

    @classmethod
    def from_raw_snapshots(cls, player_tag: str, raw_snapshots: list[dict]) -> 'PlayerSnapshotDetail':
        """Build detail from raw API snapshots (bypasses BrawlAccount parsing)

        Args:
            player_tag: Player tag
            raw_snapshots: List of dicts with 'timestamp' (ISO string) and 'brawlers' (raw API format)

        Returns:
            PlayerSnapshotDetail instance
        """
        brawler_data: dict[str, BrawlerDetail] = {}

        for snapshot in raw_snapshots:
            timestamp_iso = snapshot['timestamp']
            timestamp = datetime.fromisoformat(timestamp_iso.rstrip('Z'))

            for brawler_raw in snapshot['brawlers']:
                name = brawler_raw['name']

                # Initialize brawler detail if first time seeing this brawler
                if name not in brawler_data:
                    brawler_data[name] = BrawlerDetail()

                detail = brawler_data[name]
                detail.n += 1
                detail.timestamp.append(int(timestamp.timestamp()))
                detail.trophies.append(brawler_raw['trophies'])
                detail.power.append(brawler_raw['power'])

                # Parse gadgets
                gadgets_raw = brawler_raw.get('gadgets', [])
                detail.has_gadget1.append(True if len(gadgets_raw) > 0 else None)
                detail.has_gadget2.append(True if len(gadgets_raw) > 1 else None)

                # Parse star powers
                sp_raw = brawler_raw.get('starPowers', [])
                detail.has_sp1.append(True if len(sp_raw) > 0 else None)
                detail.has_sp2.append(True if len(sp_raw) > 1 else None)

                # Parse hypercharge
                hc_raw = brawler_raw.get('hyperCharges', [])
                detail.has_hc.append(True if len(hc_raw) > 0 else None)

                # Parse gears
                gears_raw = brawler_raw.get('gears', [])
                gear_names = {g['name'] for g in gears_raw}
                base_gears = {'SPEED', 'HEALTH', 'DAMAGE', 'VISION', 'SHIELD', 'GADGET COOLDOWN'}
                other_gears = [name for name in gear_names if name not in base_gears]

                gear_count = sum([
                    1 if 'SPEED' in gear_names else 0,
                    1 if 'HEALTH' in gear_names else 0,
                    1 if 'DAMAGE' in gear_names else 0,
                    1 if 'VISION' in gear_names else 0,
                    1 if 'SHIELD' in gear_names else 0,
                    1 if 'GADGET COOLDOWN' in gear_names else 0,
                    len(other_gears)
                ])
                detail.gear_count.append(gear_count)

                # Parse buffies
                buffies_raw = brawler_raw.get('buffies', {})
                detail.buffie_gadget.append(True if buffies_raw.get('gadget') else None)
                detail.buffie_sp.append(True if buffies_raw.get('starPower') else None)
                detail.buffie_hc.append(True if buffies_raw.get('hyperCharge') else None)

        return cls(player_tag=player_tag, brawlers=brawler_data)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return self.model_dump(exclude_none=True)

    def to_json(self) -> str:
        """Serialize to JSON string"""
        import json
        return json.dumps(self.to_dict(), indent=2)
