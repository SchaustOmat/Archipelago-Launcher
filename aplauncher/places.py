"""Where is the player? Maps game locations (OoT scene ids, SM64 courses) to German names,
the Archipelago region/location name prefixes found there, and short dungeon help texts.

The help texts describe mechanics and puzzles only: in a randomizer the items are elsewhere,
so they never claim what lies in a chest.
"""

# ---------------------------------------------------------------- Ocarina of Time
# Overworld areas: German name and the prefixes Ship of Harkinian uses for regions/locations there.
OOT_AREAS = {
    "kf": ("Kokiri-Wald", ["KF ", "Kokiri Forest"]),
    "lw": ("Verlorene Wälder", ["LW ", "Lost Woods", "Deku Theater"]),
    "sfm": ("Heilige Lichtung", ["SFM ", "Sacred Forest"]),
    "hf": ("Hylianische Steppe", ["HF ", "Hyrule Field"]),
    "llr": ("Lon Lon-Farm", ["LLR ", "Lon Lon"]),
    "market": ("Marktplatz", ["Market", "MK "]),
    "tot": ("Zitadelle der Zeit", ["ToT ", "Temple of Time", "Beyond Door of Time", "Master Sword Pedestal"]),
    "hc": ("Hyrule-Schloss", ["HC ", "Hyrule Castle", "Castle Grounds"]),
    "ogc": ("Vor Ganons Schloss", ["OGC ", "Outside Ganon"]),
    "kak": ("Kakariko", ["Kak ", "Kakariko"]),
    "gy": ("Friedhof", ["Graveyard", "The Graveyard"]),
    "dmt": ("Todesberg-Pfad", ["DMT ", "Death Mountain Trail", "Death Mountain Summit"]),
    "dmc": ("Todesberg-Krater", ["DMC ", "Death Mountain Crater"]),
    "gc": ("Goronia", ["GC ", "Goron City"]),
    "zr": ("Zora-Fluss", ["ZR ", "Zora River", "Zoras River"]),
    "zd": ("Zoras Reich", ["ZD ", "Zoras Domain"]),
    "zf": ("Zoras Quelle", ["ZF ", "Zoras Fountain"]),
    "lh": ("Hylia-See", ["LH ", "Lake Hylia"]),
    "gv": ("Gerudotal", ["GV ", "Gerudo Valley"]),
    "gf": ("Gerudo-Festung", ["GF ", "Gerudo Fortress", "Gerudos Fortress"]),
    "hw": ("Gespenster-Wüste", ["Wasteland", "HW ", "Haunted Wasteland"]),
    "col": ("Wüstenkoloss", ["Colossus", "Desert Colossus"]),
}

# Dungeons: German name, prefixes, help text.
OOT_DUNGEONS = {
    "deku": ("Deku-Baum", ["Deku Tree"], [
        "Brauchst: Schwert und Deku-Schild (gegen Gohmas Larven), Schleuder fürs Weiterkommen oben.",
        "Netze im Boden mit einem brennenden Deku-Stab (an Fackel anzünden) wegbrennen.",
        "Unten: Block in Wasser schieben, über die Plattformen zum Boss.",
        "Gohma: Auge mit Schleuder treffen, wenn es rot ist, dann zuschlagen.",
    ]),
    "dc": ("Dodongos Höhle", ["Dodongos Cavern", "Dodongo"], [
        "Brauchst: Bomben (oder Sprengkraft) – ohne geht hier fast nichts.",
        "Risse in Wänden und Augen der großen Dodongo-Statue mit Bomben öffnen.",
        "Feuer-Dodongos meiden, Bombenblumen zum Sprengen nutzen.",
        "King Dodongo: Bombe in das offene Maul, dann mit dem Schwert zuschlagen.",
    ]),
    "jabu": ("Jabu-Jabus Bauch", ["Jabu Jabu", "Jabu"], [
        "Brauchst: Bumerang ist hier der Schlüssel (Tentakel, Schalter, Gegner).",
        "Prinzessin Ruto tragen und auf Schalter/Plattformen absetzen.",
        "Rote Tentakel mit dem Bumerang durchtrennen, um Wege zu öffnen.",
        "Barinade: zuerst die Halterungen mit dem Bumerang lösen, dann Quallen und Kern treffen.",
    ]),
    "forest": ("Waldtempel", ["Forest Temple"], [
        "Eingang über den Baum in der Heiligen Lichtung (Fanghaken).",
        "Brauchst: Bogen für die vier Irrlicht-Schwestern (je eine Fackel/Farbe).",
        "Der verdrehte Gang: Augen-Schalter mit Bogen treffen, um ihn zu drehen.",
        "Blöcke im Innenhof-Bereich schieben, Kistenrätsel mit den Gemälden.",
        "Phantom-Ganon: Energiebälle mit dem Schwert zurückschlagen, Pfeile auf das Pferd.",
    ]),
    "fire": ("Feuertempel", ["Fire Temple"], [
        "Brauchst: Goronen-Rüstung (sonst Hitzeschaden) und Bomben.",
        "Eingesperrte Goronen befreien – oft hinter Schaltern und Schlüsseltüren.",
        "Stahlhammer öffnet Pfosten und Blöcke, Feuerwände mit Schaltern löschen.",
        "Volvagia: wenn der Kopf aus einem Loch kommt, mit dem Hammer draufhauen.",
    ]),
    "water": ("Wassertempel", ["Water Temple"], [
        "Brauchst: Eisenstiefel, Zora-Rüstung und Fanghaken.",
        "Wasserstand an den Triforce-Symbolen mit Zeldas Wiegenlied ändern (oben/mitte/unten).",
        "Überall nach Kristall-Schaltern und Wasserwirbeln schauen; Schlüssel gut einteilen.",
        "Dunkel-Link: Schwert schwer, besser mit Hammer/Feuer oder abwechseln.",
        "Morpha: Wasserkern mit dem Fanghaken rausziehen und zuschlagen.",
    ]),
    "shadow": ("Schattentempel", ["Shadow Temple"], [
        "Eingang am Friedhof: Fackeln mit Dins Feuerinferno anzünden.",
        "Brauchst: Auge der Wahrheit (unsichtbare Wände/Böden) und Gleitstiefel.",
        "Bomben für Wände; Riesensense und Fallen mit Timing umgehen.",
        "Bongo Bongo: mit Auge der Wahrheit Hände betäuben (Pfeile), dann ins Auge schießen.",
    ]),
    "spirit": ("Geistertempel", ["Spirit Temple"], [
        "Teils als Kind, teils als Erwachsener – Kind-Teil durch das kleine Loch.",
        "Brauchst: Silberhandschuhe (Erwachsener) bzw. Schleuder/Bomben (Kind).",
        "Spiegelschild: Licht auf Sonnensymbole lenken, um Türen und Wege zu öffnen.",
        "Twinrova: Feuer/Eis mit dem Spiegelschild aufnehmen und zurückschießen.",
    ]),
    "botw": ("Grund des Brunnens", ["Bottom of the Well"], [
        "Nur als Kind; Brunnen in Kakariko leer machen (Hymne des Sturms in der Mühle).",
        "Auge der Wahrheit zeigt falsche Wände und Löcher – viele Fallen.",
        "Dead Hand: nicht zu nah an die Hände, auf den Kopf zielen.",
    ]),
    "ice": ("Eishöhle", ["Ice Cavern"], [
        "Eingang hinter dem König Zora in Zoras Quelle (als Erwachsener).",
        "Blaues Feuer in Flaschen sammeln, damit rotes Eis schmelzen.",
        "Eisblock-Rätsel: Block so schieben, dass er an den Silberrubinen vorbeirutscht.",
    ]),
    "gtg": ("Gerudo-Trainingsarena", ["Gerudo Training"], [
        "Brauchst: Gerudo-Mitgliedskarte für den Eintritt.",
        "Viele Räume mit Zeitlimit und Silberrubinen; Schlüssel öffnen die Mitte.",
        "Hilfreich: Bogen, Fanghaken, Eisenstiefel, Hammer, Auge der Wahrheit.",
    ]),
    "hideout": ("Diebesversteck", ["Thieves Hideout", "Gerudo Fortress Jail", "Hideout"], [
        "Zimmerleute befreien: Wächterinnen mit Pfeilen/Fanghaken betäuben.",
        "Erwischt werden heißt Gefängnis – leise von hinten an die Wachen.",
    ]),
    "gc_castle": ("Ganons Schloss", ["Ganon's Castle", "Ganons Castle"], [
        "Prüfungen (je nach Einstellung) brauchen Lichtpfeile, Feuerpfeile, Auge der Wahrheit u. a.",
        "Boss-Schlüssel nötig für den Turm (siehe Ziel oben).",
    ]),
    "gc_tower": ("Ganons Turm", ["Ganon's Tower", "Ganons Tower", "Ganondorf's Lair", "Ganon's Arena"], [
        "Ganondorf: Energiebälle zurückschlagen, dann Lichtpfeil und zuschlagen.",
        "Ganon: Schwanz treffen; Master-Schwert nötig für den letzten Schlag.",
    ]),
}

_DUNGEON_SCENES = {0: "deku", 17: "deku", 1: "dc", 18: "dc", 2: "jabu", 19: "jabu", 3: "forest", 20: "forest",
                   4: "fire", 21: "fire", 5: "water", 22: "water", 6: "spirit", 23: "spirit", 7: "shadow",
                   24: "shadow", 8: "botw", 9: "ice", 11: "gtg", 12: "hideout", 13: "gc_castle", 15: "gc_castle",
                   10: "gc_tower", 14: "gc_tower", 25: "gc_tower", 26: "gc_tower", 79: "gc_tower"}

# Interiors and grottos count as the area they belong to.
_AREA_SCENES = {
    85: "kf", 40: "kf", 41: "kf", 38: "kf", 39: "kf", 45: "kf", 52: "kf",
    91: "lw", 86: "sfm", 81: "hf", 99: "llr", 54: "llr", 76: "llr",
    27: "market", 28: "market", 29: "market", 30: "market", 31: "market", 32: "market", 33: "market", 34: "market",
    43: "market", 44: "market", 49: "market", 50: "market", 51: "market", 53: "market", 66: "market",
    75: "market", 77: "market", 16: "market",
    35: "tot", 36: "tot", 37: "tot", 67: "tot",
    95: "hc", 69: "hc", 70: "hc", 74: "hc", 59: "hc", 100: "ogc", 61: "ogc",
    82: "kak", 42: "kak", 48: "kak", 55: "kak", 72: "kak", 78: "kak", 80: "kak",
    83: "gy", 58: "gy", 63: "gy", 64: "gy", 65: "gy",
    96: "dmt", 97: "dmc", 98: "gc", 46: "gc",
    84: "zr", 88: "zd", 47: "zd", 89: "zf",
    87: "lh", 56: "lh", 73: "lh",
    90: "gv", 57: "gv", 93: "gf", 94: "hw", 92: "col",
}


def oot_place(scene: int):
    """(name, prefixes, help lines or [], is_dungeon) for a SoH scene number, or None if unknown."""
    if scene in _DUNGEON_SCENES:
        name, prefixes, tips = OOT_DUNGEONS[_DUNGEON_SCENES[scene]]
        return name, prefixes, tips, True
    if scene in _AREA_SCENES:
        name, prefixes = OOT_AREAS[_AREA_SCENES[scene]]
        return name, prefixes, [], False
    if scene == 62:
        return "Grotte", [], [], False
    return None


# ---------------------------------------------------------------- Super Mario 64
# Course number (gCurrCourseNum) -> German/English name and location prefixes used by the AP world.
SM64_COURSES = {
    1: ("Bob-omb Battlefield", ["BoB:", "Bob-omb Battlefield"]),
    2: ("Whomp's Fortress", ["WF:", "Whomp's Fortress"]),
    3: ("Jolly Roger Bay", ["JRB:", "Jolly Roger Bay"]),
    4: ("Cool, Cool Mountain", ["CCM:", "Cool, Cool Mountain"]),
    5: ("Big Boo's Haunt", ["BBH:", "Big Boo's Haunt"]),
    6: ("Hazy Maze Cave", ["HMC:", "Hazy Maze Cave"]),
    7: ("Lethal Lava Land", ["LLL:", "Lethal Lava Land"]),
    8: ("Shifting Sand Land", ["SSL:", "Shifting Sand Land"]),
    9: ("Dire, Dire Docks", ["DDD:", "Dire, Dire Docks"]),
    10: ("Snowman's Land", ["SL:", "Snowman's Land"]),
    11: ("Wet-Dry World", ["WDW:", "Wet-Dry World"]),
    12: ("Tall, Tall Mountain", ["TTM:", "Tall, Tall Mountain"]),
    13: ("Tiny-Huge Island", ["THI:", "Tiny-Huge Island"]),
    14: ("Tick Tock Clock", ["TTC:", "Tick Tock Clock"]),
    15: ("Rainbow Ride", ["RR:", "Rainbow Ride"]),
    16: ("Bowser in the Dark World", ["Bowser in the Dark World"]),
    17: ("Bowser in the Fire Sea", ["Bowser in the Fire Sea"]),
    18: ("Bowser in the Sky", ["Bowser in the Sky"]),
    19: ("Princess's Secret Slide", ["The Princess's Secret Slide"]),
    20: ("Cavern of the Metal Cap", ["Cavern of the Metal Cap"]),
    21: ("Tower of the Wing Cap", ["Tower of the Wing Cap"]),
    22: ("Vanish Cap under the Moat", ["Vanish Cap Under the Moat"]),
    23: ("Wing Mario over the Rainbow", ["Wing Mario Over the Rainbow"]),
    24: ("Secret Aquarium", ["The Secret Aquarium"]),
}
SM64_CASTLE_PREFIXES = ["Toad", "MIPS", "Castle"]

SM64_TIPS = {
    16: ["Rote Münzen und den Bowser-Schlüssel gibt es hier; Bowser am Schwanz packen und gegen eine Bombe werfen."],
    17: ["Plattformen kippen und sinken – zügig weiter. Bowser gegen die Bomben am Rand werfen."],
    18: ["Letzter Bowser: dreimal gegen Bomben werfen; die Arena zerbricht nach dem ersten Treffer."],
}


def sm64_place(course: int):
    """(name, prefixes, tips, is_level) for a SM64 course number."""
    if course in SM64_COURSES:
        name, prefixes = SM64_COURSES[course]
        return name, prefixes, SM64_TIPS.get(course, []), True
    return "Schloss", SM64_CASTLE_PREFIXES, [], False


def place_name(loc: dict) -> str:
    """German area/dungeon/course name for an in-logic location (falls back to its region)."""
    groups = [(n, p) for n, p, _ in OOT_DUNGEONS.values()] + list(OOT_AREAS.values()) + list(SM64_COURSES.values())
    for name, prefixes in groups:
        if matches(loc, prefixes):
            return name
    if matches(loc, SM64_CASTLE_PREFIXES):
        return "Schloss"
    return loc.get("region") or "?"


def matches(loc: dict, prefixes) -> bool:
    """Is an in-logic location (from the bridge snapshot) inside the place with these prefixes?"""
    name, region = loc.get("name", ""), loc.get("region", "")
    return any(name.startswith(p) or region.startswith(p) for p in prefixes)
