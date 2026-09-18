# Brawl Stars API Documentation

Quick reference for API endpoints, response formats, and quirks.

## Endpoints

```
BASE: https://api.brawlstars.com/v1
Auth: Bearer {token} (or proxy with no auth)
```

### GET /players/{tag}
Player account data. Returns single player.

**Response:** `{ tag, name, trophies, highestTrophies, 3vs3Victories, soloVictories, duoVictories, club: {tag, name}, brawlers: [...] }`

**Brawler object:**
- `name, power, trophies, highestTrophies, rank, prestigeLevel`
- `gadgets: [{id, name}]` (max 2)
- `starPowers: [{id, name}]` (max 2)
- `hyperCharges: [{id, name}]` (max 1)
- `buffies: {gadget: bool, starPower: bool, hyperCharge: bool}`
- `gears: [{id, name, level}]` (6 base + extras)

**Quirks:**
- `gadgets/starPowers/gears` can be `null` instead of `[]`
- `power/trophies` can be `-1` (unknown/placeholder)

### GET /players/{tag}/battlelog
Recent battles (up to 25). Returns dict with items array.

**Response:** `{ items: [...], paging: {...} }`

**Battle item:**
```json
{
  "battleTime": "20260324T234127.000Z",
  "event": {"id": int, "map": str, "mode": str, "modeId": int},
  "battle": {
    "mode": str,
    "type": str,  // "ranked" | "soloRanked" | "friendly" | null
    ...mode-specific fields
  }
}
```

### GET /clubs/{tag}
Club data + member list.

**Response:** `{ tag, name, members: [{tag, name, trophies, ...}] }`

### GET /brawlers
All brawlers metadata.

**Response:** `{ items: [{name, id, ...}] }`

## Battle Modes

### Team Modes (3v3, 5v5)
`brawlBall, gemGrab, bounty, knockout, hotZone, heist, wipeout`

**Structure:**
- `result: "victory" | "defeat"`
- `duration: int`
- `teams: [[player, player, player], [player, player, player]]`
- `starPlayer: {tag, name, brawler}`
- `trophyChange: int` (same for all teammates)

### Showdown Modes
`soloShowdown, duoShowdown, trioShowdown`

**Structure:**
- `rank: 1-10` (placement)
- `teams: [[player, player], ...]` or `players: [player, ...]` (solo)
- `trophyChange: int` **QUIRK: Only for battle owner, not in teams**
- No `result`, `duration`, `starPlayer`

**Trophy change quirk:**
- Each player gets different `trophyChange` based on their trophy level
- API only returns `trophyChange` for the player whose battlelog you fetched
- Other players in same battle have no `trophyChange` data

### Duels
1v1 with 3 brawlers each.

**Structure:**
- `players: [{tag, name, brawlers: [brawler, brawler, brawler]}]` (2 players)
- `result: "victory" | "defeat"`
- `duration: int`
- Each brawler has own `trophyChange`
- No battle-level `trophyChange`, no `starPlayer`

### PvE Modes
`lastStand`

**Structure:**
- `mode: "lastStand"`, `event.mode: "unknown"`
- `players: [...]`
- `result: "victory" | "defeat"`
- `type: null`
- No `trophyChange`

## Data Quirks

- Event `map` can be `null`
- Star player can be `null`
- Type can be `null` (PvE modes)
- Brawler ID format: `16000XXX`
- Gadget/SP/HC ID format: `23000XXX`
- Gear ID format: `62000XXX`
