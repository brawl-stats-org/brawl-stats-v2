"""What each card's tokens mean: `<VALUEn>` recipes, and overrides for bad `<!path>` tokens.

Keyed by card Name. Every entry was checked in game: the checked values live in
review/*.done (enforced by `brawlify review --check`), the reasoning in
docs/brawlify/tokens/recipe-notes.md.
"""

from brawlify.core.dump import Row
from brawlify.tokens import schema
from brawlify.tokens.combinators import Delta, Div, Loss, Percent, Ratio, Recipe, Share

OF_MAX_HEALTH = Percent("card.value", "card.character.maxhealth.scalestattolevel")
VALUE2_OF_MAX_HEALTH = Percent("card.value2", "card.character.maxhealth.scalestattolevel")
ACCESSORY_OF_MAX_HEALTH = Percent(
    "card.accessory.value1", "card.character.maxhealth.scalestattolevel"
)
OF_MAIN_ATTACK = Percent("card.value", "card.character.weaponskill.damage.scaletolevel")

RECIPES: dict[str, dict[str, Recipe]] = {
    # Alli
    "Stalker_gadget_1": {
        "VALUE1": "card.accessory.value1",
    },
    "Stalker_gadget_2": {
        "VALUE2": "card.accessory.activeticks.ticksasseconds",
    },
    "Stalker_unique_1": {
        "VALUE1": "card.value.ticksasseconds",
    },
    # Angelo
    "InsectMan_gadget": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
        "VALUE2": Percent(
            "card.accessory.customobject.areaeffectobject.customvalue",
            "card.accessory.customobject.areaeffectobject.damage.scaletolevel",
        ),
    },
    "InsectMan_ulti": {
        "VALUE1": "card.skill.areaeffectobject.timems.msasseconds",
    },
    "InsectMan_unique": {
        "VALUE1": OF_MAX_HEALTH,
    },
    # Ash
    "Knight_Heal": {
        "VALUE1": ACCESSORY_OF_MAX_HEALTH,
    },
    "Knight_Rage": {
        "VALUE1": "card.accessory.value1",
        "VALUE2": "card.accessory.value2",
    },
    # Barley
    "Barkeep_HealPotion": {
        "VALUE1": Percent("card.accessory.value2.abs", "card.character.maxhealth.scalestattolevel"),
    },
    "Barkeep_unique": {
        "VALUE1": OF_MAX_HEALTH,
    },
    # Bea
    "BeeSniper_ExtraBee": {
        "VALUE1": "card.accessory.value1",
        "VALUE2": Percent(
            "card.accessory.value2", "card.character.weaponskill.damage.scaletolevel"
        ),
    },
    # Belle
    "ElectroSniper_unique_2": {
        "VALUE2": "card.value2.ticksasseconds",
    },
    # Berry
    "Painter_gatget": {
        "VALUE1": "card.accessory.areaeffect.damage.scaledamage",
    },
    "Painter_gatget_2": {
        "VALUE1": "card.accessory.value1",
    },
    # Bo
    "BowDude_MineTrigger": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    "BowDude_unique": {
        "VALUE1": "card.value.asextravisionpercent",
    },
    "BowDude_unique_2": {
        "VALUE1": "card.value.ticksasseconds",
    },
    # Bolt
    "Rock_gadget": {
        "VALUE1": "card.accessory.value1",
        "VALUE2": "card.accessory.value2",
    },
    # Bonnie
    "CannonGirl_Dash": {
        "VALUE1": Percent(
            "card.accessory.value4",
            "card.character.ultiskill.summonedcharacter.weaponskill.damage.scaletolevel",
        ),
    },
    "CannonGirl_overcharge": {
        "VALUE1": "card.character.ultiskill.overchargedareaeffectobject.statuseffectenemy.duration.ticksasseconds",
    },
    "CannonGirl_unique": {
        "VALUE1": Share("card.value", "card.character.ultiskill.castingrange"),
    },
    "CannonGirl_unique_2": {
        "VALUE1": "card.character.weaponskill.projectile.chainbullet.damagepercentstart",
    },
    # Brock
    "RocketGirl_unique": {
        "VALUE1": Ratio(
            Div("card.value", "card.value2"),
            Div("card.character.ultiskill.activetime", "card.character.ultiskill.msbetweenattacks"),
        ),
    },
    # Buster
    "ShieldTank_Heal": {
        "VALUE1": Percent(
            "card.accessory.areaeffect.damage.abs", "card.character.maxhealth.scalestattolevel"
        ),
    },
    # Buzz
    "RopeDude_Vision": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    "RopeDude_unique": {
        "VALUE1": "card.value.ticksasseconds",
    },
    "RopeDude_unique_2": {
        "VALUE1": Ratio("card.areaeffect.radius", "areaEffect[RopeDudeSuperChargeArea].radius"),
    },
    # Byron
    "SnakeOil_Heal": {
        "VALUE1": ACCESSORY_OF_MAX_HEALTH,
        "VALUE2": "card.accessory.activeticks.ticksasseconds",
    },
    "SnakeOil_Spread": {
        "VALUE1": "card.accessory.value1",
        "VALUE2": Loss(
            "card.accessory.statuseffectenemy.damage",
            "card.character.weaponskill.projectile.statuseffectenemy.damage",
        ),
        "VALUE3": Loss(
            "card.accessory.statuseffectally.healing",
            "card.character.weaponskill.projectile.statuseffectally.healing",
        ),
    },
    "SnakeOil_unique": {
        "VALUE1": "card.value",
        "VALUE2": "card.value2.ticksasseconds",
    },
    "SnakeOil_unique_2": {
        "VALUE1": "card.value.ticksasseconds",
    },
    # Carl
    "Whirlwind_Trail": {
        "VALUE1": "card.accessory.customobject.statuseffectenemy.damage.scaletolevel",
    },
    "Whirlwind_unique": {
        "VALUE1": Share("card.value", "card.character.weaponskill.projectile.speed"),
    },
    # Charlie
    "Cocooner_CocoonSelf": {
        "VALUE1": "card.accessory.value1",
    },
    "Cocooner_SpawnPets": {
        "VALUE1": "card.accessory.value1",
    },
    "Cocooner_unique_2": {
        "VALUE1": "card.areaeffect.timems.msasseconds",
    },
    # Chester
    "Jester_RandomBuff": {
        "VALUE1": "card.accessory.value1.ticksasseconds",
    },
    # Clancy
    "Crab_gadget": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    "Crab_gadget_2": {
        "VALUE1": "card.accessory.value3.ammounits",
    },
    # Colt
    "Gunslinger_unique_2": {
        "VALUE1": Share("card.value", "card.character.weaponskill.castingrange"),
    },
    # Cordelius
    "Duelist_Silence": {
        "VALUE1": "card.accessory.customobject.silencedurationms.msasseconds",
    },
    # Crow
    "Crow_unique_2": {
        "VALUE1": "card.value2",
        "VALUE2": "card.value",
    },
    # Darryl
    "BarrelBot_Slow": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    "BarrelBot_Spin": {
        "VALUE1": Percent(
            "card.accessory.value3", "card.character.weaponskill.damage.scaletolevel"
        ),
        "VALUE2": "card.accessory.value2",
    },
    "BarrelBot_overcharge": {
        "VALUE1": "areaEffect[BarrelBotOverchargeChargeArea].damage.scaletolevel",
    },
    "BarrelBot_unique": {
        "VALUE1": "card.statuseffect.duration.ticksasseconds",
        "VALUE2": "card.statuseffect.shieldpercent",
    },
    "BarrelBot_unique_2": {
        "VALUE1": "card.value.ticksasseconds",
    },
    # Doug
    "Reviver_ulti": {
        "VALUE1": "card.value",
    },
    "Reviver_unique_2": {
        "VALUE1": OF_MAIN_ATTACK,
    },
    # Draco
    "DragonRider_gatget_2": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    "DragonRider_unique": {
        "VALUE1": "card.value.ticksasseconds",
        "VALUE2": "card.statuseffect.damagereceivedboostpercent",
        "VALUE3": "card.statuseffect.duration.ticksasseconds",
    },
    "DragonRider_unique_2": {
        "VALUE1": OF_MAX_HEALTH,
    },
    # Dynamike
    "TntDude_Stun": {
        "VALUE1": "card.accessory.value1.ticksasseconds",
    },
    "TntDude_unique_2": {
        "VALUE1": OF_MAIN_ATTACK,
    },
    # El Primo
    "Luchador_unique": {
        "VALUE1": "card.statuseffect.damage.scaletolevel",
    },
    # Emz
    "Mummy_unique_2": {
        "VALUE1": OF_MAX_HEALTH,
    },
    # Eve
    "Flea_unique_2": {
        "VALUE1": "card.value.ticksasseconds",
    },
    # Fang
    "KickerDude_Mines": {
        "VALUE1": Percent(
            "card.accessory.value3", "card.character.weaponskill.damage.scaletolevel"
        ),
    },
    "KickerDude_Sweep": {
        "VALUE1": "card.accessory.areaeffect.customvalue1.ticksasseconds",
    },
    "KickerDude_unique_2": {
        "VALUE1": "card.value.ticksasseconds",
        "VALUE2": VALUE2_OF_MAX_HEALTH,
        "VALUE3": "card.value3",
    },
    # Finx
    "Chronomancer_gadget_1": {
        "VALUE1": "card.accessory.value1.ticksasseconds",
    },
    "Chronomancer_gadget_2": {
        "VALUE1": "card.accessory.statuseffectenemy.duration.ticksasseconds",
    },
    "Chronomancer_unique_2": {
        "VALUE1": "card.value.ticksasseconds",
    },
    # Frank
    "HammerDude_unique_2": {
        "VALUE1": OF_MAX_HEALTH,
    },
    # Gale
    "Blower_unique": {
        "VALUE1": "card.value.ticksasseconds",
    },
    # Geishatransformed
    "GeishaTransformed_ulti": {
        "VALUE1": "card.skill.onchargehitstatuseffect.duration.ticksasseconds",
    },
    # Gene
    "HookDude_Homing": {
        "VALUE2": Percent(
            "card.accessory.value2", "card.character.weaponskill.damage.scaletolevel"
        ),
    },
    "HookDude_Push": {
        "VALUE1": "card.accessory.value1",
    },
    "HookDude_unique": {
        "VALUE1": OF_MAX_HEALTH,
    },
    "HookDude_unique_2": {
        "VALUE1": OF_MAIN_ATTACK,
    },
    # Gigi
    "Daredevil_gadget_2": {
        "VALUE1": "card.accessory.areaeffect.timems.msasseconds",
    },
    "Daredevil_ulti": {
        "VALUE1": "card.skill.castingtime.msasseconds",
        "VALUE2": "card.character.component.values.ticksasseconds",
    },
    "Daredevil_unique_1": {
        "VALUE1": "card.statuseffect.ultichargeboostpercent",
        "VALUE2": "card.value.ticksasseconds",
    },
    "Daredevil_unique_2": {
        "VALUE1": "card.value.scalestattolevel",
    },
    # Glowy
    "Mender_gadget_1": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    "Mender_overcharge": {
        "VALUE1": "statusEffect[MenderUltiOverchargedDamageReceiveBoost].damagereceivedboostpercent",
    },
    "Mender_unique": {
        "VALUE1": "statusEffect[MenderStarPowerEnemyDamageDebuff].damagereducepercent",
        "VALUE2": "statusEffect[MenderStarPowerAllyDamageBuff].damageboostpercent",
    },
    # Grom
    "CrossBomber_Burst": {
        "VALUE1": "card.character.weaponskill.maxammo",
    },
    # Gus
    "SoulCollector_ExplodeSouls": {
        "VALUE1": "card.character.weaponskill.damage.scaletolevel",
    },
    # Hank
    "FishTank_Shield": {
        "VALUE1": "card.accessory.shieldpercent",
        "VALUE2": "card.accessory.shieldticks.ticksasseconds",
    },
    "FishTank_Slow": {
        "VALUE1": "card.accessory.value1.ticksasseconds",
    },
    # Jacky
    "Driller_overcharge": {
        "VALUE1": "card.value.ticksasseconds",
    },
    # Jae-Yong
    "Alternator_gadget_1": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    "Alternator_gadget_2": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    # Janet
    "JetpackGirl_DamageTower": {
        "VALUE1": "card.accessory.customobject.areaeffect.damage.scaledamage",
    },
    # Jessie
    "Mechanic_TurretBuff": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    "Mechanic_unique": {
        "VALUE1": OF_MAIN_ATTACK,
    },
    "Mechanic_unique_2": {
        "VALUE1": Share(
            "projectile[MechanicOverchargedTurretElecProj].chaintraveldistance",
            "card.character.ultiskill.summonedcharacter.autoattackrange",
        ),
    },
    # Juju
    "Voodoo_overcharge": {
        "VALUE1": "card.value",
        "VALUE2": "card.value2",
        "VALUE3": "card.value3.asspeedpercent",
    },
    # Kaze
    "Geisha_abi": {
        "VALUE1": "card.skill.areaeffectobject2.customvalue1",
    },
    "Geisha_gadget_1": {
        "VALUE1": "card.accessory.value1",
        "VALUE2": "card.accessory.statuseffectally.duration.ticksasseconds",
    },
    "Geisha_unique_1": {
        "VALUE1": "card.statuseffect.speedreducepercent",
        "VALUE2": "card.statuseffect.duration.ticksasseconds",
    },
    "Geisha_unique_2": {
        "VALUE1": "card.areaeffect.customvalue1",
    },
    # Kenji
    "Samurai_gadget": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    "Samurai_gadget_2": {
        "VALUE1": "card.accessory.value2",
        "VALUE2": "card.accessory.value1.ticksasseconds",
    },
    "Samurai_unique_2": {
        "VALUE1": "card.value",
        "VALUE2": "card.statuseffect.shieldpercent",
    },
    # Kit
    "Attacher_gadget": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
        "VALUE2": "card.accessory.value1",
    },
    "Attacher_gadget_1": {
        "VALUE1": "card.accessory.value1",
    },
    "Attacher_unique": {
        "VALUE1": "card.value2",
    },
    "Attacher_unique_2": {
        "VALUE1": "card.value.ticksasseconds",
    },
    # Larry & Lawrie
    "Twins_gatget_1": {
        "VALUE1": "card.accessory.value3",
    },
    # Lily
    "Ambusher_gadget": {
        "VALUE1": "card.accessory.value1.ticksasseconds",
    },
    "Ambusher_overcharge": {
        "VALUE1": "card.value.ticksasseconds",
    },
    "Ambusher_unique": {
        "VALUE1": OF_MAIN_ATTACK,
    },
    # Lola
    "Duplicator_StaticDuplicate": {
        "VALUE1": "card.accessory.value1",
        "VALUE2": "card.accessory.activeticks.ticksasseconds",
    },
    "Duplicator_Swap": {
        "VALUE1": ACCESSORY_OF_MAX_HEALTH,
    },
    "Duplicator_unique_2": {
        "VALUE1": OF_MAIN_ATTACK,
    },
    # Lou
    "IceDude_AreaFreeze": {
        "VALUE1": "card.accessory.value1",
    },
    "IceDude_Freeze": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    "IceDude_unique": {
        "VALUE1": Ratio("card.value", "areaEffect[IceDudeUltiArea].customvalue2"),
    },
    "IceDude_unique_2": {
        "VALUE1": "card.statuseffect.damagereducepercent",
    },
    # Lumi
    "Morningstar_gadget_1": {
        "VALUE1": "card.accessory.areaeffect.timems.msasseconds",
        "VALUE2": "card.accessory.areaeffect.damage.scaledamage",
    },
    "Morningstar_gadget_2": {
        "VALUE1": "card.accessory.areaeffect.timems.msasseconds",
    },
    "Morningstar_unique_1": {
        "VALUE1": "card.areaeffect.timems.msasseconds",
        "VALUE2": Percent(
            "card.areaeffect[2].damage",
            "card.character.ultiskill.damage.scaletolevel.escalatetolastring",
        ),
    },
    # Maisie
    "Maisie_Dash": {
        "VALUE1": "card.accessory.areaeffect.customvalue1.ticksasseconds",
    },
    "Maisie_ReloadAndDamage": {
        "VALUE1": "card.accessory.value1.ammounits",
        "VALUE2": "card.accessory.value2",
    },
    "Maisie_unique_2": {
        "VALUE2": "card.statuseffect.duration.ticksasseconds",
    },
    # Mandy
    "Beamer_unique": {
        "VALUE1": Share("card.value", "card.character.weaponskill.projectile.speed"),
    },
    # Meeple
    "Meeple_gadget": {
        "VALUE1": "card.accessory.customobject.damage.scaletolevel",
    },
    "Meeple_ulti": {
        "VALUE1": "card.skill.projectile.spawnareaeffectobject.timems.msasseconds",
    },
    "Meeple_unique": {
        "VALUE1": "card.value.scalestattolevel",
    },
    # Meg
    "MechaDude_Heal": {
        "VALUE1": Percent("card.accessory.value1", "card.character.pet.maxhealth.scalestattolevel"),
        "VALUE2": "card.accessory.activeticks.ticksasseconds",
    },
    "MechaDude_unique": {
        "VALUE1": "card.value",
        "VALUE2": "card.value2.ticksasseconds",
    },
    # Melodie
    "AxeJuggler_gatget": {
        "VALUE1": "card.accessory.value1",
        "VALUE2": "card.accessory.value2",
        "VALUE3": "card.accessory.activeticks.ticksasseconds",
    },
    "AxeJuggler_gatget_1": {
        "VALUE1": "card.accessory.value1",
    },
    "AxeJuggler_overcharge": {
        "VALUE1": "card.value",
    },
    # Mico
    "Leaper_gatget_1": {
        "VALUE1": "card.accessory.value1",
    },
    "Leaper_overcharge": {
        "VALUE1": "areaEffect[LeaperOverchargedUltiAreaExplosion].stunticks.ticksasseconds",
    },
    "Leaper_unique": {
        "VALUE1": "card.value.ticksasseconds",
    },
    # Mina
    "Dancer_gadget_1": {
        "VALUE1": "card.accessory.areaeffect.timems.msasseconds",
    },
    # Moe
    "Digger_gadget": {
        "VALUE1": "card.accessory.value2",
        "VALUE2": "card.accessory.activeticks.ticksasseconds",
    },
    # Mortis
    "Undertaker_unique_2": {
        "VALUE1": "card.value.ticksasseconds",
    },
    # Mr. P
    "SpawnerDude_Promote": {
        "VALUE1": Percent(
            "card.accessory.value1", "card.character.weaponskill.damage.scaletolevel"
        ),
        "VALUE2": Percent("card.accessory.value2", "card.character.maxhealth.scalestattolevel"),
    },
    "SpawnerDude_unique": {
        "VALUE1": "card.value.msasseconds",
        "VALUE2": "card.value2",
    },
    # Nani
    "Controller_BounceBack": {
        "VALUE1": "card.accessory.value1",
        "VALUE2": "card.accessory.activeticks.ticksasseconds",
    },
    "Controller_unique": {
        "VALUE1": OF_MAIN_ATTACK,
    },
    # Nita
    "Shaman_overcharge": {
        "VALUE1": "card.value",
        "VALUE3": "card.value3.asspeedpercent",
    },
    "Shaman_unique": {
        "VALUE1": "card.value.petdamagepercent",
        "VALUE2": "card.value2.characterdamagepercent",
    },
    # Ollie
    "Skater_gatget": {
        "VALUE1": "card.accessory.statuseffectenemy.duration.ticksasseconds",
    },
    "Skater_gatget_2": {
        "VALUE1": "card.accessory.statuseffectenemy.duration.ticksasseconds",
    },
    "Skater_ulti": {
        "VALUE1": "card.skill.areaeffectobject2.chainareaeffect.statuseffectenemy.damage.scaletolevel",
        "VALUE2": "card.skill.areaeffectobject2.chainareaeffect.statuseffectenemy.duration.ticksasseconds",
        "VALUE3": "card.skill.areaeffectobject2.statuseffectself.ammoreducepercent",
    },
    # Otis
    "Silencer_BigProjectiles": {
        "VALUE1": Percent(
            "card.accessory.value4", "card.character.weaponskill.damage.scaletolevel"
        ),
        "VALUE2": "card.accessory.customobject.spawnareaeffectobject.timems.msasseconds",
    },
    "Silencer_overcharge": {
        "VALUE1": "statusEffect[SilencerUltiOvercharged].duration.ticksasseconds",
    },
    "Silencer_unique": {
        "VALUE1": Ratio("card.value", "card.character.ultiskill.projectile.spawnitem.lifetime"),
    },
    "Silencer_unique_2": {
        "VALUE1": Ratio(
            Div("card.value", "card.character.weaponskill.msbetweenattacks"),
            Div(
                "card.character.weaponskill.activetime",
                "card.character.weaponskill.msbetweenattacks",
            ),
        ),
    },
    # Pam
    "MinigunDude_AmmoSink": {
        "VALUE1": "card.accessory.value1",
        "VALUE2": "card.accessory.value2",
    },
    "MinigunDude_BurstHeal": {
        "VALUE1": "card.accessory.petareaeffect.damage.scaledamage",
    },
    "MinigunDude_unique": {
        "VALUE1": OF_MAX_HEALTH,
    },
    "MinigunDude_unique_2": {
        "VALUE1": OF_MAX_HEALTH,
    },
    # Pearl
    "Cooker_Healing": {
        "VALUE1": "card.accessory.statuseffectally.healingtotal.scaletolevel",
    },
    "Cooker_Poison": {
        "VALUE1": "card.accessory.statuseffectenemy.damagetotal.scaletolevel",
    },
    "Cooker_overcharge": {
        "VALUE1": "areaEffect[CookerOverchargedUltiArea].timems.msasseconds",
    },
    # Penny
    "ArtilleryDude_overcharge": {
        "VALUE1": "card.character.ultiskill.summonedcharacter.autoattackbulletspershot",
    },
    "ArtilleryDude_unique": {
        "VALUE1": Ratio("card.value", "card.character.weaponskill.projectile.chainspread"),
    },
    "ArtilleryDude_unique_2": {
        "VALUE1": OF_MAIN_ATTACK,
    },
    # Pierce
    "Bulletstorm_gadget_1": {
        "VALUE1": "card.accessory.value1",
    },
    "Bulletstorm_gadget_2": {
        "VALUE1": "card.accessory.value1",
    },
    "Bulletstorm_overcharge": {},
    "Bulletstorm_unique_1": {
        "VALUE1": "card.statuseffect.speedreducepercent",
    },
    # Piper
    "Sniper_HandGun": {
        "VALUE2": Percent(
            "card.accessory.value2", "card.character.weaponskill.damage.scaletolevel"
        ),
    },
    "Sniper_unique": {
        "VALUE1": OF_MAIN_ATTACK,
    },
    "Sniper_unique_2": {
        "VALUE1": "card.value.ammounits",
    },
    # Poco
    "DeadMariachi_unique": {
        "VALUE1": OF_MAX_HEALTH,
    },
    # R-T
    "SplitterLegs_ulti": {
        "VALUE1": "card.value3",
    },
    # Rico
    "TrickshotDude_unique": {
        "VALUE1": OF_MAIN_ATTACK,
    },
    # Rosa
    "Rosa_unique": {
        "VALUE1": OF_MAX_HEALTH,
    },
    "Rosa_unique_2": {
        "VALUE1": OF_MAIN_ATTACK,
    },
    # Ruffs
    "Ruffs_AirStrike": {
        "VALUE1": Percent(
            "card.accessory.value1", "card.character.weaponskill.damage.scaletolevel"
        ),
    },
    "Ruffs_Cover": {
        "VALUE1": "card.accessory.value1",
        "VALUE2": "card.accessory.value4",
    },
    # Sandy
    "Sandstorm_Sleep": {
        "VALUE1": "card.accessory.activationdelay.ticksasseconds",
    },
    "Sandstorm_StunSleep": {
        "VALUE1": "card.accessory.value1.ticksasseconds",
    },
    "Sandstorm_overcharge": {
        "VALUE1": "statusEffect[SandStormOverchargedAreaSpeedBoost].speedboostpercent",
        "VALUE2": "areaEffect[SandStormOverchargedUltiSilenceArea].customvalue1.ticksasseconds",
    },
    "Sandstorm_unique": {
        "VALUE1": OF_MAIN_ATTACK,
    },
    "Sandstorm_unique_2": {
        "VALUE1": Percent("card.value.abs", "card.character.maxhealth.scalestattolevel"),
    },
    # Shelly
    "ShotgunGirl_unique_2": {
        "VALUE1": "card.value",
        "VALUE2": VALUE2_OF_MAX_HEALTH,
        "VALUE3": "card.value3.msasseconds",
    },
    # Sprout
    "Wally_Heal": {
        "VALUE1": ACCESSORY_OF_MAX_HEALTH,
    },
    "Wally_unique": {
        "VALUE1": "card.value.msasseconds",
    },
    # Squeak
    "StickyBomb_Range": {
        "VALUE1": Share("card.accessory.value3", "card.character.weaponskill.castingrange"),
        "VALUE2": "card.accessory.value1",
    },
    "StickyBomb_Vision": {
        "VALUE1": "card.accessory.areaeffect.timems.msasseconds",
    },
    "StickyBomb_unique_2": {
        "VALUE2": "card.statuseffect.duration.ticksasseconds",
    },
    # Stu
    "Roller_MegaStunt": {
        "VALUE1": Percent(
            "card.accessory.value1", "card.character.weaponskill.damage.scaletolevel"
        ),
    },
    "Roller_unique": {
        "VALUE1": Share("card.value", "card.character.ultiskill.castingrange"),
    },
    "Roller_unique_2": {
        "VALUE1": OF_MAX_HEALTH,
    },
    # Tara
    "BlackHole_Shadows": {
        "VALUE1": "card.accessory.value3.ticksasseconds",
    },
    "BlackHole_Vision": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    # Tick
    "ClusterBombDude_Explosion": {
        "VALUE1": "card.accessory.activationdelay.ticksasseconds",
        "VALUE2": "card.character.weaponskill.damage.scaletolevel",
        "VALUE3": "card.accessory.shieldpercent",
    },
    "ClusterBombDude_ExtraMines": {
        "VALUE1": "card.accessory.value1",
    },
    "ClusterBombDude_overcharge": {
        "VALUE1": "accessory[ClusterBombDude_ExtraMines].value1",
    },
    "ClusterBombDude_unique": {
        "VALUE1": "card.value.ticksasseconds",
    },
    "ClusterBombDude_unique_2": {
        "VALUE1": Share("card.value", "card.character.weaponskill.rechargetime"),
    },
    # Trunk
    "Domain_abi": {
        "VALUE1": "statusEffect[DomainOnAreaBuff].speedboostpercent",
        "VALUE2": "statusEffect[DomainOnAreaBuff].damageboostpercent",
    },
    "Domain_gadget_2": {
        "VALUE1": "card.accessory.statuseffectally.duration.ticksasseconds",
    },
    "Domain_unique_1": {
        "VALUE1": "statusEffect[DomainDamageReduceSP].damagereducepercent",
    },
    # Wendy
    "FutureGirl_overcharge": {
        "VALUE": "statusEffect[FutureGirlTurretAreaStatusEffectOvercharged].damagepercentredirecttosource",
    },
    "FutureGirl_ulti": {
        "VALUE": "statusEffect[FutureGirlTurretAreaStatusEffect].damagepercentredirecttosource",
    },
    # Willow
    "Puppeteer_Dive": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    "Puppeteer_MoreDamage": {
        "VALUE1": Percent(
            "card.accessory.value1", "statusEffect[PuppeteerPoison].damagetotal.scaletolevel"
        ),
    },
    "Puppeteer_ulti": {
        "VALUE1": "card.skill.projectile.customuniquepropertyvalue.ticksasseconds",
        "VALUE2": "card.value2",
    },
    # Ziggy
    "Fury_gadget_1": {
        "VALUE1": "card.accessory.activeticks.ticksasseconds",
    },
    "Fury_unique_1": {
        "VALUE2": "card.statuseffect.duration.ticksasseconds",
        "VALUE3": "card.statuseffect.speedreducepercent",
    },
    "Fury_unique_2": {
        "VALUE1": Ratio(
            "skill[FuryWeaponSp].damage.scaletolevel",
            "card.character.weaponskill.damage.scaletolevel",
        ),
    },
}

OVERRIDES: dict[str, dict[str, Recipe]] = {
    # 8-Bit
    "Arcade_unique": {
        "arcade.largerAreaUlti.rangePercent": Ratio(
            "card.areaeffect.radius", "areaEffect[DamageBoost].radius"
        ),
        "arcade.largerAreaUlti.damageDelta": Delta(
            "card.areaeffect.statuseffectself.damageboostpercent",
            "statusEffect[ArcadeDamageBoostAllies].damageboostpercent",
        ),
    },
    # Bo
    "BowDude_unique": {
        "card.value1_legacy_spot": "card.value.asextravisionpercent",
    },
    # Bull
    "BullDude_Heal": {
        "card.accessory.skill.projectile.statusEffectSelfOnHit.healing": "card.accessory.skill.projectile.statuseffectselfonhit.healing.scaletolevel",
    },
    "BullDude_overcharge": {
        "card.character.overchargeShieldPercent": "card.value",
    },
    # Colt
    "Gunslinger_unique_2": {
        "card.value1.attackRangeIncreasePercent": "card.value.attackrangeincreasepercent",
    },
    # Cosmo
    "Attractor_abi": {
        "card.skill.projectile.component[0].values[0]": "card.skill.projectile.projectileskin.component[0].values[0]",
    },
    # Meg
    "MechaDude_Heal": {
        "buddy.accessory.additionalactivetime.ticksasseconds": "buddy.accessory.activetime.ticksasseconds",
    },
    "MechaDude_unique_2": {
        "buddy.component.values[0].aspercentagefrom100steal": "buddy.component.values[1].ammounits",
    },
}


def override_for(token: str, card: Row | None) -> Recipe | None:
    """The recipe replacing a `<!path>` token on this card, or None: the path then means itself."""
    if card is None:
        return None
    return OVERRIDES.get(card["Name"], {}).get(token)


def recipe_for(token: str, card: Row | None) -> Recipe | None:
    """What `<VALUEn>` means on this card, or None when nobody knows.

    A card listed in RECIPES is described entirely there: a missing slot is a
    deliberate hole and never falls back to the positional default.
    """
    if card is None:
        return None
    if card["Name"] in RECIPES:
        return RECIPES[card["Name"]].get(token)
    template = schema.POSITIONAL_DEFAULTS.get(card["MetaType"])
    if template is None:
        return None
    slot = token.removeprefix("VALUE") or "1"
    return template.format(n=slot)
