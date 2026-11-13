"""Facts about the csv the walker needs: hops, column aliases, deduced constants.

Data only, no imports. Evidence for every constant: docs/brawlify/tokens/constants.md.
"""

TICKS_PER_SECOND = 20
BASE_BUSH_VISION_TILES = 2
ULTI_CHARGE_UNITS_PER_PERCENT = 40
AMMO_UNITS_PER_SHOT = 100
BASE_SPEED_UNITS = 1000

ROOT_TABLES = {
    "areaeffect": "area_effects_logic",
    "statuseffect": "status_effects_logic",
    "skill": "skills",
    "projectile": "projectiles_logic",
    "accessory": "accessories",
}
"""Roots that name their row, as in `areaEffect[FireDudePetrolFireOvercharged].timeMs`."""

HOPS: dict[str, tuple[str | None, str | tuple[str, ...]]] = {
    "accessory": ("Skill", "accessories"),
    "skill": ("Skill", "skills"),
    "character": ("Target", "characters"),
    "weaponskill": ("WeaponSkill", "skills"),
    "ultiskill": ("UltimateSkill", "skills"),
    "summonedcharacter": (None, "characters"),
    "overchargedsummonedcharacter": ("OverchargedSummonedCharacters", "characters"),
    "statuseffect": (None, "status_effects_logic"),
    "statuseffectally": (None, "status_effects_logic"),
    "statuseffectenemy": (None, "status_effects_logic"),
    "statuseffectself": (None, "status_effects_logic"),
    "component": ("Components", "components_logic"),
    "trait": ("Traits", "traits"),
    "projectile": ("Projectiles", "projectiles_logic"),
    "areaeffect": (None, "area_effects_logic"),
    # Tried in order. `characters` must stay last: 4 names exist in both
    # characters and area_effects_logic, and those mean the area.
    "customobject": (
        "CustomObject",
        ("skills", "area_effects_logic", "projectiles_logic", "characters"),
    ),
    "customobjectprojectile": ("CustomObject", "projectiles_logic"),
    "areaeffectobject": ("AreaEffectObject", "area_effects_logic"),
    "overchargedareaeffectobject": ("OverchargedAreaEffectObject", "area_effects_logic"),
    "overchargedversion": ("OverchargedVersion", "skills"),
    "pet": ("Pet", "characters"),
    "petareaeffect": ("PetAreaEffect", "area_effects_logic"),
    "overchargedprojectile": ("OverchargedProjectiles", "projectiles_logic"),
    "statuseffectselfonhit": (None, "status_effects_logic"),
    "onchargehitselfstatuseffect": (None, "status_effects_logic"),
    "onchargehitstatuseffect": (None, "status_effects_logic"),
    "activationselfstatuseffect": (None, "status_effects_logic"),
    # The column pluralises mid-word, which the segment+"s" deduction cannot reach.
    "activationselfstatuseffectovercharged": (
        "ActivationSelfStatusEffectsOvercharged",
        "status_effects_logic",
    ),
    "action": ("Actions", "actions"),
    "onenemyhitaction": ("OnEnemyHitActions", "actions"),
    "actionsoncancelondamage": ("ActionsOnCancelOnDamage", "actions"),
    "customobjectitem": ("CustomObject", "items_logic"),
    "triggerareaeffect": ("TriggerAreaEffect", "area_effects_logic"),
    "spawnareaeffectobject": ("SpawnAreaEffectObject", "area_effects_logic"),
    "chainareaeffect": ("ChainAreaEffect", "area_effects_logic"),
    "spawnitem": ("SpawnItem", "items_logic"),
    "spawneditem": ("SpawnedItem", "items_logic"),
    "areaeffectobject2": ("AreaEffectObject2", "area_effects_logic"),
    "chainbullet": ("ChainBullet", "projectiles_logic"),
    "bulletexplosionbullet": ("BulletExplosionBullet", "projectiles_logic"),
    # A projectile's skin row carries the same Name as its logic row.
    "projectileskin": ("Name", "projectiles_skin"),
}
"""Segment -> (column holding a row name, destination table or tables).

A None column is deduced from the segment name. The fixed column is only used
when the current row has it: `accessory` reads Skill on a card, Accessory on a buddy.
"""

ALIASES = {
    "value": ("Value", "CustomValue1"),
    "value1": ("Value", "CustomValue1"),
    "value2": ("Value2", "CustomValue2"),
    "value3": ("Value3", "CustomValue3"),
    "value4": ("Value4", "CustomValue4"),
    "customvalue1": ("CustomValue1", "CustomValue"),
    "duration": ("DurationTicks",),
    "maxhealth": ("Hitpoints",),
    "maxammo": ("MaxCharge",),
    "areaeffect": ("AreaEffect", "AreaEffectObject"),
    "statuseffect": ("StatusEffect", "StatusEffectAlly", "StatusEffectSelf", "StatusEffectEnemy"),
    "activetime": ("ActiveTime", "ActiveTicks"),
}
"""Segment -> candidate columns, first one present in the row wins."""

POSITIONAL_DEFAULTS = {
    4: "card.value{n}",
    6: "card.value{n}",
}
"""MetaType -> what `<VALUEn>` means on a card with no recipe. Star powers and hypercharges only."""

DAMAGE_SCALE = {
    0: None,
    1: "card.character.weaponskill.damage.scaletolevel",
    2: "card.character.maxhealth.scalestattolevel",
}
"""`area_effects_logic.DamageScaleType` -> path of the base `Damage` is a percentage of.

None means absolute. Types 3 to 6 are not decoded and stay unresolved on purpose.
"""
