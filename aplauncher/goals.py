"""Turns a bridge snapshot (slot data + items) into German goal lines for the overlay."""

from .i18n import _

STONES = ["Kokiri's Emerald", "Goron's Ruby", "Zora's Sapphire"]
MEDALLIONS = ["Forest Medallion", "Fire Medallion", "Water Medallion",
              "Spirit Medallion", "Shadow Medallion", "Light Medallion"]


class Step:
    def __init__(self, label, have=None, need=None, done=None, hint=""):
        self.label, self.have, self.need, self.hint = label, have, need, hint
        self.done = done if done is not None else (need is not None and have is not None and have >= need)


def _count(items, names):
    return sum(1 for n in names if items.get(n))


def _soh_requirement(kind, sd, prefix, items, what):
    """Shared by rainbow bridge and Ganon's boss key (LACS): both use the same requirement types."""
    stones, meds = _count(items, STONES), _count(items, MEDALLIONS)
    if kind == "stones":
        return Step(what + ": " + _("Heilige Steine"), stones, sd.get(f"{prefix}_stones_required", 3))
    if kind == "medallions":
        return Step(what + ": " + _("Amulette"), meds, sd.get(f"{prefix}_medallions_required", 6))
    if kind == "dungeon_rewards":
        return Step(what + ": " + _("Steine + Amulette"), stones + meds, sd.get(f"{prefix}_dungeon_rewards_required", 9))
    if kind == "dungeons":
        return Step(what + ": " + _("Dungeons abschließen"), None, sd.get(f"{prefix}_dungeons_required", 8),
                    hint=_("Zählt nach dem blauen Warp hinter dem Boss."))
    if kind == "tokens":
        return Step(what + ": " + _("Goldene Skulltulas"), items.get("Gold Skulltula Token", 0),
                    sd.get(f"{prefix}_skull_tokens_required", 50))
    if kind == "greg":
        return Step(what + ": " + _("Greg (grüner Rubin) finden"), 1 if items.get("Greg the Green Rupee") else 0, 1)
    return None


def soh_steps(sd, items, beaten):
    steps = []
    bridge = sd.get("rainbow_bridge", 7)
    if bridge == 0:
        have = _count(items, ["Shadow Medallion", "Spirit Medallion"]) + (1 if items.get("Light Arrows") else 0)
        steps.append(Step(_("Regenbogenbrücke: Schatten- + Geist-Amulett + Lichtpfeile"), have, 3))
    elif bridge == 1:
        steps.append(Step(_("Regenbogenbrücke ist offen"), done=True))
    else:
        kinds = {2: "stones", 3: "medallions", 4: "dungeon_rewards", 5: "dungeons", 6: "tokens", 7: "greg"}
        s = _soh_requirement(kinds.get(bridge), sd, "rainbow_bridge", items, _("Brücke"))
        if s:
            steps.append(s)

    bk = sd.get("ganons_castle_boss_key", 5)
    if bk >= 2:
        kinds = {2: None, 3: "stones", 4: "medallions", 5: "dungeon_rewards", 6: "dungeons", 7: "tokens"}
        s = _soh_requirement(kinds.get(bk), sd, "ganons_castle_boss_key", items, _("Ganons Boss-Schlüssel"))
        if bk == 2:
            have = _count(items, ["Shadow Medallion", "Spirit Medallion"])
            s = Step(_("Ganons Boss-Schlüssel: Schatten- + Geist-Amulett"), have, 2)
        if s:
            s.hint = (s.hint + " " if s.hint else "") + _("Danach in der Zitadelle der Zeit abholen (Zelda-Szene).")
            steps.append(s)
    else:
        steps.append(Step(_("Ganons Boss-Schlüssel finden"), 1 if items.get("Ganon's Castle Boss Key") else 0, 1))

    if sd.get("ganons_trials") == 1 and sd.get("ganons_trials_count", 0):
        steps.append(Step(_("Ganons Schloss: {n} Prüfungen").format(n=sd["ganons_trials_count"]), None, None,
                          done=False))
    if sd.get("triforce_hunt"):
        need = sd.get("triforce_hunt_pieces_required") or sd.get("triforce_hunt_pieces_total", 30)
        steps.append(Step(_("Triforce-Splitter"), items.get("Triforce Piece", 0), need))
    else:
        steps.append(Step(_("Ganon besiegen"), done=False))
    return steps


def sm64_steps(sd, items, beaten):
    stars = items.get("Power Star", 0)
    finish = sd.get("StarsToFinish", 70)
    steps = []
    doors = [(_("1. Bowser-Tür"), sd.get("FirstBowserDoorCost", 8)),
             (_("Keller-Tür"), sd.get("BasementDoorCost", 30)),
             (_("Obergeschoss-Tür"), sd.get("SecondFloorDoorCost", 50))]
    for label, cost in doors:
        if stars < cost:
            steps.append(Step(_("Nächste Sterntür: {door}").format(door=label), stars, cost))
            break
    keys = items.get("Progressive Key", 0)
    basement = bool(items.get("Basement Key")) or keys >= 1
    upstairs = bool(items.get("Second Floor Key")) or keys >= 2
    steps.append(Step(_("Keller-Schlüssel"), 1 if basement else 0, 1))
    steps.append(Step(_("Obergeschoss-Schlüssel"), 1 if upstairs else 0, 1))
    what = _("alle Bowser-Level") if sd.get("CompletionType") == 1 else _("letzter Bowser")
    steps.append(Step(_("Sterne für das Ende ({what})").format(what=what), stars, finish))
    return steps


def steps_for(snapshot):
    sd = snapshot.get("slot_data") or {}
    items = snapshot.get("items") or {}
    beaten = snapshot.get("beaten", False)
    game = snapshot.get("game")
    if game == "Ship of Harkinian":
        return soh_steps(sd, items, beaten)
    if game == "Super Mario 64":
        return sm64_steps(sd, items, beaten)
    return []
