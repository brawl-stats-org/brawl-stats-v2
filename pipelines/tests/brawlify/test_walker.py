from brawlify.tokens.combinators import Percent, Ratio, value_of
from brawlify.tokens.walker import Walker

TABLES = {
    "accessories": {"Dash": {"Name": "Dash", "Skill": "DashSkill", "CustomValue1": 40}},
    "skills": {
        "DashSkill": {"Name": "DashSkill", "Damage": 500},
        "Weapon": {"Name": "Weapon", "Damage": 1000},
    },
    "characters": {"Hero": {"Name": "Hero", "Hitpoints": 3000, "WeaponSkill": "Weapon"}},
    "traits": {"Packed": {"Name": "Packed", "Value": "60;1000"}},
}
CARD = {"Name": "Card", "Skill": "Dash", "Target": "Hero", "Value": 10, "Traits": "Packed;"}
ROOTS = {"card": CARD}
walker = Walker({**{name: {} for name in ("area_effects_logic", "projectiles_logic")}, **TABLES})


def resolve(path):
    return walker.resolve(path, ROOTS)


def test_hops_then_reads():
    assert resolve("card.accessory.skill.damage") == 500


def test_alias_reads_custom_value():
    assert resolve("card.accessory.value1") == 40


def test_modifier_applies_to_a_number():
    assert resolve("card.accessory.value1.ticksAsSeconds") == 2


def test_level_scaling_doubles_at_power_eleven():
    assert resolve("card.character.maxhealth.scaleToLevel") == 6000


def test_packed_cell_slots():
    assert resolve("card.trait.value") == 60
    assert resolve("card.trait.value2") == 1000


def test_unknown_column_is_unresolved_not_an_error():
    assert resolve("card.accessory.nothinghere") is None


def test_named_root():
    assert walker.resolve("skill[Weapon].damage", {}) == 1000


def test_combinators():
    assert value_of(Percent("card.value", "card.character.maxhealth"), ROOTS, walker) == 300
    assert (
        value_of(Ratio("card.accessory.skill.damage", "skill[Weapon].damage"), ROOTS, walker) == -50
    )
