"""
NORNBRAIN Test Harness - Unit Test Suite
=========================================

Tests for tools/test_harness.py.

These tests do NOT require a running engine. They verify:
  1. Constants (metarooms, drives, food classifiers, genus names)
  2. CAOS command generation (via *_caos_cmd functions - return lists of CAOS strings)
  3. CLI argument parsing (build_parser)
  4. Safety invariants (egg layer, genus IDs, GAME var prefix, reward/punishment chems)
  5. Mock-based dispatch tests (patch caos() and verify call args)

Integration tests (need running engine on TCP 20001) are marked with
@pytest.mark.integration and skipped by default.

Usage:
    pytest tests/test_harness_test.py -v
    pytest tests/test_harness_test.py -v -m "not integration"

All *_caos_cmd functions return a LIST of CAOS strings. Tests join them
into a single string for substring assertions.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup - tools/ is not a package; inject it into sys.path
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_THIS_DIR, ".."))
_TOOLS = os.path.join(_ROOT, "tools")

if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

# ---------------------------------------------------------------------------
# Module import - cached after first successful load
# ---------------------------------------------------------------------------
_harness = None


def _get_harness():
    global _harness
    if _harness is None:
        try:
            import test_harness as th
            _harness = th
        except ImportError as exc:
            pytest.skip(f"tools/test_harness.py not importable: {exc}")
    return _harness


def _join(cmds) -> str:
    """Flatten a list of CAOS strings into one string for substring tests."""
    if isinstance(cmds, list):
        return "\n".join(cmds)
    return cmds


# ===========================================================================
# 1. CONSTANTS TESTS
# ===========================================================================


class TestMetaroomConstants:
    """Verify METAROOMS lookup table completeness and coordinate accuracy."""

    EXPECTED = {
        "norn-terrarium": (0, 1190, 712),
        "ettin-desert":   (1, 5190, 704),
        "aquatic":        (2, 9000, 1200),
        "grendel-jungle": (3, 1948, 2310),
        "corridor":       (4, 3200, 1100),
        "pinball":        (5, 6000, 2000),
        "space":          (6, 9000, 500),
        "learning-room":  (7, 2360, 467),
        "crypt":          (8, 3200, 2500),
    }

    def test_all_nine_metarooms_present(self):
        th = _get_harness()
        assert len(th.METAROOMS) == 9, (
            f"Expected 9 metarooms, got {len(th.METAROOMS)}: {list(th.METAROOMS)}"
        )

    def test_metaroom_keys(self):
        th = _get_harness()
        assert set(th.METAROOMS.keys()) == set(self.EXPECTED.keys())

    def test_metaroom_coordinates_all(self):
        th = _get_harness()
        for name, expected in self.EXPECTED.items():
            actual = th.METAROOMS[name]
            assert actual == expected, (
                f"METAROOMS[{name!r}] = {actual}, expected {expected}"
            )

    def test_norn_terrarium(self):
        assert _get_harness().METAROOMS["norn-terrarium"] == (0, 1190, 712)

    def test_ettin_desert(self):
        assert _get_harness().METAROOMS["ettin-desert"] == (1, 5190, 704)

    def test_aquatic(self):
        assert _get_harness().METAROOMS["aquatic"] == (2, 9000, 1200)

    def test_grendel_jungle(self):
        assert _get_harness().METAROOMS["grendel-jungle"] == (3, 1948, 2310)

    def test_corridor(self):
        assert _get_harness().METAROOMS["corridor"] == (4, 3200, 1100)

    def test_pinball(self):
        assert _get_harness().METAROOMS["pinball"] == (5, 6000, 2000)

    def test_space(self):
        assert _get_harness().METAROOMS["space"] == (6, 9000, 500)

    def test_learning_room(self):
        # Often mis-spelled; verify exact key and value
        assert _get_harness().METAROOMS["learning-room"] == (7, 2360, 467)

    def test_crypt(self):
        assert _get_harness().METAROOMS["crypt"] == (8, 3200, 2500)

    def test_entries_are_3_tuples_of_ints(self):
        th = _get_harness()
        for name, entry in th.METAROOMS.items():
            assert isinstance(entry, tuple) and len(entry) == 3, (
                f"{name}: expected 3-tuple, got {entry!r}"
            )
            mr_id, x, y = entry
            assert isinstance(mr_id, int), f"{name}: metaroom_id must be int, got {type(mr_id)}"
            assert isinstance(x, int), f"{name}: x must be int, got {type(x)}"
            assert isinstance(y, int), f"{name}: y must be int, got {type(y)}"

    def test_metaroom_ids_are_unique(self):
        th = _get_harness()
        ids = [v[0] for v in th.METAROOMS.values()]
        assert len(ids) == len(set(ids)), f"Duplicate metaroom IDs: {ids}"


class TestDriveConstants:
    """Verify DRIVES index completeness and name accuracy."""

    EXPECTED = {
        0: "pain", 1: "hunger_protein", 2: "hunger_carb", 3: "hunger_fat",
        4: "coldness", 5: "hotness", 6: "tiredness", 7: "sleepiness",
        8: "loneliness", 9: "crowdedness", 10: "fear", 11: "boredom",
        12: "anger", 13: "sex_drive", 14: "injury", 15: "suffocation",
        16: "thirst", 17: "stress", 18: "backlash", 19: "comfort",
    }

    def test_all_20_drives_present(self):
        th = _get_harness()
        assert len(th.DRIVES) == 20, f"Expected 20 drives, got {len(th.DRIVES)}"

    def test_drive_indices_0_through_19(self):
        assert set(_get_harness().DRIVES.keys()) == set(range(20))

    def test_all_drive_names(self):
        th = _get_harness()
        for idx, expected_name in self.EXPECTED.items():
            assert th.DRIVES[idx] == expected_name, (
                f"DRIVES[{idx}] = {th.DRIVES[idx]!r}, expected {expected_name!r}"
            )

    def test_drive_0_is_pain_not_reward(self):
        """Drive 0 is pain - this is NOT the reward chemical."""
        assert _get_harness().DRIVES[0] == "pain"

    def test_comfort_is_last_drive(self):
        assert _get_harness().DRIVES[19] == "comfort"

    def test_all_drive_values_are_strings(self):
        th = _get_harness()
        for idx, name in th.DRIVES.items():
            assert isinstance(name, str), f"DRIVES[{idx}] is not a string: {name!r}"


class TestFoodItemConstants:
    """Verify FOOD_ITEMS classifier tuples against game-files-analysis.md."""

    EXPECTED = {
        "fruit":   (2, 8, 0),
        "cheese":  (2, 11, 1),
        "carrot":  (2, 11, 3),
        "plant":   (2, 4, 0),
        "seed":    (2, 3, 0),
    }

    def test_all_food_items_present(self):
        th = _get_harness()
        assert set(th.FOOD_ITEMS.keys()) == set(self.EXPECTED.keys())

    def test_all_classifiers_correct(self):
        th = _get_harness()
        for name, expected in self.EXPECTED.items():
            assert th.FOOD_ITEMS[name] == expected, (
                f"FOOD_ITEMS[{name!r}] = {th.FOOD_ITEMS[name]}, expected {expected}"
            )

    def test_fruit_is_2_8_0(self):
        """Fruit must be (2, 8, 0) - not (2, 6, 0) or any other."""
        assert _get_harness().FOOD_ITEMS["fruit"] == (2, 8, 0)

    def test_carrot_genus_is_11(self):
        """Carrot is genus 11, species 3. Injects alcohol (chem 75). NOT genus 6."""
        f, g, s = _get_harness().FOOD_ITEMS["carrot"]
        assert g == 11, f"carrot genus must be 11, got {g}"
        assert s == 3, f"carrot species must be 3, got {s}"

    def test_all_food_items_are_family_2(self):
        th = _get_harness()
        for name, (f, g, s) in th.FOOD_ITEMS.items():
            assert f == 2, f"FOOD_ITEMS[{name!r}] family={f}, expected 2"

    def test_food_items_are_3_tuples(self):
        th = _get_harness()
        for name, entry in th.FOOD_ITEMS.items():
            assert isinstance(entry, tuple) and len(entry) == 3, (
                f"FOOD_ITEMS[{name!r}] must be (family, genus, species) 3-tuple, got {entry!r}"
            )


class TestGenusNamesConstant:
    """Verify GENUS_NAMES: 1=norn, 2=grendel, 3=ettin."""

    def test_genus_1_is_norn(self):
        assert _get_harness().GENUS_NAMES[1].lower() == "norn"

    def test_genus_2_is_grendel(self):
        assert _get_harness().GENUS_NAMES[2].lower() == "grendel"

    def test_genus_3_is_ettin(self):
        assert _get_harness().GENUS_NAMES[3].lower() == "ettin"

    def test_no_genus_0(self):
        """There is no genus 0 creature."""
        assert 0 not in _get_harness().GENUS_NAMES


# ===========================================================================
# 2. CAOS COMMAND GENERATION TESTS
#
# All *_caos_cmd() functions return a LIST of CAOS strings.
# We join them into one string for substring assertions.
# ===========================================================================


class TestSpawnEggsCmd:
    """spawn_eggs_caos_cmd must use Norn Egg Layer (3 3 31), never NEW:."""

    def test_returns_a_list(self):
        result = _get_harness().spawn_eggs_caos_cmd(n=1)
        assert isinstance(result, list), f"Expected list, got {type(result)}"

    def test_uses_egg_layer_classifier_3_3_31(self):
        cmd = _join(_get_harness().spawn_eggs_caos_cmd(n=1))
        assert "3 3 31" in cmd, (
            f"spawn_eggs CAOS must target egg layer (3 3 31):\n{cmd}"
        )

    def test_uses_enum_to_scope_egg_layer(self):
        cmd = _join(_get_harness().spawn_eggs_caos_cmd(n=1))
        assert "enum 3 3 31" in cmd, (
            f"Expected 'enum 3 3 31' to scope to egg layer:\n{cmd}"
        )

    def test_sends_mesg_writ_activate(self):
        """Egg layer is activated via mesg writ, not direct NEW: or hatch."""
        cmd = _join(_get_harness().spawn_eggs_caos_cmd(n=1))
        assert "mesg wrt" in cmd.lower(), (
            f"spawn_eggs must use mesg writ to activate egg layer:\n{cmd}"
        )

    def test_no_direct_new_command(self):
        """Must NOT use NEW: commands for spawning norns."""
        cmd = _join(_get_harness().spawn_eggs_caos_cmd(n=2))
        assert "new:" not in cmd.lower(), (
            f"spawn_eggs must NOT use NEW: - only egg layer activation:\n{cmd}"
        )

    def test_closes_enum_with_next(self):
        cmd = _join(_get_harness().spawn_eggs_caos_cmd(n=1))
        assert "next" in cmd.lower(), f"enum must close with 'next':\n{cmd}"

    def test_n_1_returns_one_cmd(self):
        result = _get_harness().spawn_eggs_caos_cmd(n=1)
        assert len(result) == 1, f"n=1 should return 1 CAOS string, got {len(result)}"

    def test_n_3_returns_three_cmds(self):
        result = _get_harness().spawn_eggs_caos_cmd(n=3)
        assert len(result) == 3, f"n=3 should return 3 CAOS strings, got {len(result)}"

    def test_full_caos_pattern(self):
        """Full expected pattern: enum 3 3 31 ... mesg wrt+ targ 1001 0 0 0 ... next."""
        cmd = _join(_get_harness().spawn_eggs_caos_cmd(n=1)).lower()
        assert "enum 3 3 31" in cmd
        assert "mesg wrt" in cmd
        assert "next" in cmd


class TestHatchAllCmd:
    """hatch_all_caos_cmd must skip incubation on creature eggs (3 4 1)."""

    def test_returns_a_list(self):
        assert isinstance(_get_harness().hatch_all_caos_cmd(), list)

    def test_targets_egg_classifier_3_4_0(self):
        cmd = _join(_get_harness().hatch_all_caos_cmd())
        assert "3 4 1" in cmd, f"hatch_all must target eggs (3 4 0):\n{cmd}"

    def test_uses_enum_3_4_0(self):
        cmd = _join(_get_harness().hatch_all_caos_cmd())
        assert "enum 3 4 1" in cmd, f"Expected 'enum 3 4 1':\n{cmd}"

    def test_uses_pose_3_and_tick(self):
        cmd = _join(_get_harness().hatch_all_caos_cmd())
        assert "pose 3" in cmd, f"hatch_all must use pose 3 to skip incubation:\n{cmd}"
        assert "tick" in cmd, f"hatch_all must use tick after pose:\n{cmd}"

    def test_closes_with_next(self):
        cmd = _join(_get_harness().hatch_all_caos_cmd())
        assert "next" in cmd.lower()

    def test_full_caos_pattern(self):
        cmd = _join(_get_harness().hatch_all_caos_cmd()).lower()
        assert "enum 3 4 1" in cmd
        assert "pose 3" in cmd
        assert "tick" in cmd
        assert "next" in cmd


class TestKillGrendelsCmd:
    """kill_grendels_caos_cmd must target genus 2 (grendels), never genus 1 (norns)."""

    def test_returns_a_list(self):
        assert isinstance(_get_harness().kill_grendels_caos_cmd(), list)

    def test_targets_family_4_genus_2(self):
        cmd = _join(_get_harness().kill_grendels_caos_cmd())
        assert "4 2 0" in cmd, (
            f"kill_grendels must target family 4 genus 2 (grendels):\n{cmd}"
        )

    def test_uses_enum_4_2_0(self):
        cmd = _join(_get_harness().kill_grendels_caos_cmd())
        assert "enum 4 2 0" in cmd

    def test_does_not_target_norns_genus_1(self):
        """CRITICAL safety: must never accidentally kill norns."""
        cmd = _join(_get_harness().kill_grendels_caos_cmd())
        assert "4 1 0" not in cmd, (
            f"kill_grendels must NOT target genus 1 (norns):\n{cmd}"
        )

    def test_uses_kill_targ(self):
        cmd = _join(_get_harness().kill_grendels_caos_cmd()).lower()
        assert "kill targ" in cmd, f"kill_grendels must use 'kill targ':\n{cmd}"

    def test_closes_with_next(self):
        cmd = _join(_get_harness().kill_grendels_caos_cmd()).lower()
        assert "next" in cmd

    def test_full_caos_pattern(self):
        cmd = _join(_get_harness().kill_grendels_caos_cmd()).lower()
        assert "enum 4 2 0" in cmd
        assert "kill targ" in cmd
        assert "next" in cmd


class TestKillEttinsCmd:
    """kill_ettins_caos_cmd must target genus 3 (ettins), never genus 1 or 2."""

    def test_returns_a_list(self):
        assert isinstance(_get_harness().kill_ettins_caos_cmd(), list)

    def test_targets_family_4_genus_3(self):
        cmd = _join(_get_harness().kill_ettins_caos_cmd())
        assert "4 3 0" in cmd, (
            f"kill_ettins must target family 4 genus 3 (ettins):\n{cmd}"
        )

    def test_uses_enum_4_3_0(self):
        cmd = _join(_get_harness().kill_ettins_caos_cmd())
        assert "enum 4 3 0" in cmd

    def test_does_not_target_norns(self):
        cmd = _join(_get_harness().kill_ettins_caos_cmd())
        assert "4 1 0" not in cmd, "kill_ettins must NOT target genus 1 (norns)"

    def test_does_not_target_grendels(self):
        cmd = _join(_get_harness().kill_ettins_caos_cmd())
        assert "4 2 0" not in cmd, "kill_ettins must NOT target genus 2 (grendels)"

    def test_full_caos_pattern(self):
        cmd = _join(_get_harness().kill_ettins_caos_cmd()).lower()
        assert "enum 4 3 0" in cmd
        assert "kill targ" in cmd
        assert "next" in cmd


class TestTeleportCameraCmd:
    """teleport_camera_caos_cmd must emit cmra X Y 0 with correct coordinates."""

    def test_returns_a_list(self):
        result = _get_harness().teleport_camera_caos_cmd("norn-terrarium")
        assert isinstance(result, list)

    def test_norn_terrarium(self):
        cmd = _join(_get_harness().teleport_camera_caos_cmd("norn-terrarium"))
        assert "cmra 1190 712 0" in cmd

    def test_ettin_desert(self):
        cmd = _join(_get_harness().teleport_camera_caos_cmd("ettin-desert"))
        assert "cmra 5190 704 0" in cmd

    def test_aquatic(self):
        cmd = _join(_get_harness().teleport_camera_caos_cmd("aquatic"))
        assert "cmra 9000 1200 0" in cmd

    def test_grendel_jungle(self):
        cmd = _join(_get_harness().teleport_camera_caos_cmd("grendel-jungle"))
        assert "cmra 1948 2310 0" in cmd

    def test_corridor(self):
        cmd = _join(_get_harness().teleport_camera_caos_cmd("corridor"))
        assert "cmra 3200 1100 0" in cmd

    def test_pinball(self):
        cmd = _join(_get_harness().teleport_camera_caos_cmd("pinball"))
        assert "cmra 6000 2000 0" in cmd

    def test_space(self):
        cmd = _join(_get_harness().teleport_camera_caos_cmd("space"))
        assert "cmra 9000 500 0" in cmd

    def test_learning_room(self):
        cmd = _join(_get_harness().teleport_camera_caos_cmd("learning-room"))
        assert "cmra 2360 467 0" in cmd

    def test_crypt(self):
        cmd = _join(_get_harness().teleport_camera_caos_cmd("crypt"))
        assert "cmra 3200 2500 0" in cmd

    def test_all_metarooms_produce_correct_cmra(self):
        """Exhaustive: every metaroom produces the right cmra X Y 0 command."""
        th = _get_harness()
        for name, (mr_id, x, y) in th.METAROOMS.items():
            cmd = _join(th.teleport_camera_caos_cmd(name))
            expected = f"cmra {x} {y} 0"
            assert expected in cmd, (
                f"teleport_camera_caos_cmd({name!r}) should contain {expected!r}:\n{cmd}"
            )

    def test_invalid_metaroom_raises(self):
        th = _get_harness()
        with pytest.raises((ValueError, KeyError)):
            th.teleport_camera_caos_cmd("not-a-real-metaroom")

    def test_uses_zero_smoothing_flag(self):
        """Third cmra argument should be 0 (instant camera move, no smooth scroll)."""
        cmd = _join(_get_harness().teleport_camera_caos_cmd("norn-terrarium"))
        assert cmd.strip().endswith("0"), f"cmra should end with 0, got:\n{cmd}"


class TestActivateAllGadgetsCmd:
    """activate_all_gadgets_caos_cmd must target machinery (3 3 0) and gadgets (3 8 0)."""

    def test_returns_a_list(self):
        assert isinstance(_get_harness().activate_all_gadgets_caos_cmd(), list)

    def test_returns_at_least_two_commands(self):
        result = _get_harness().activate_all_gadgets_caos_cmd()
        assert len(result) >= 2, (
            f"Expected at least 2 CAOS commands (machinery + gadgets), got {len(result)}"
        )

    def test_targets_machinery_3_3_0(self):
        cmd = _join(_get_harness().activate_all_gadgets_caos_cmd())
        assert "3 3 0" in cmd, f"activate_all_gadgets must target machinery (3 3 0):\n{cmd}"

    def test_targets_gadgets_3_8_0(self):
        cmd = _join(_get_harness().activate_all_gadgets_caos_cmd())
        assert "3 8 0" in cmd, f"activate_all_gadgets must target gadgets (3 8 0):\n{cmd}"

    def test_uses_enum_3_3_0(self):
        cmd = _join(_get_harness().activate_all_gadgets_caos_cmd())
        assert "enum 3 3 0" in cmd

    def test_uses_enum_3_8_0(self):
        cmd = _join(_get_harness().activate_all_gadgets_caos_cmd())
        assert "enum 3 8 0" in cmd

    def test_uses_mesg_writ(self):
        cmd = _join(_get_harness().activate_all_gadgets_caos_cmd()).lower()
        assert "mesg wrt" in cmd

    def test_does_not_target_norns(self):
        """Must not accidentally activate creatures (family 4)."""
        cmd = _join(_get_harness().activate_all_gadgets_caos_cmd())
        assert "enum 4" not in cmd, "activate_all_gadgets must not target creatures (family 4)"


class TestInjectRewardCmd:
    """inject_reward_caos_cmd must use CHEM 204, NOT 49, 35, or any other."""

    def test_returns_a_list(self):
        assert isinstance(_get_harness().inject_reward_caos_cmd(amount=0.5), list)

    def test_reward_uses_chem_204(self):
        cmd = _join(_get_harness().inject_reward_caos_cmd(amount=0.5))
        assert "chem 204" in cmd.lower(), (
            f"inject_reward must use CHEM 204:\n{cmd}"
        )

    def test_reward_amount_appears_in_cmd(self):
        cmd = _join(_get_harness().inject_reward_caos_cmd(amount=0.5))
        assert "0.5" in cmd, f"Amount 0.5 should appear in reward CAOS:\n{cmd}"

    def test_reward_amount_1_0(self):
        cmd = _join(_get_harness().inject_reward_caos_cmd(amount=1.0))
        assert "1.0" in cmd or "1.0000" in cmd, f"Amount 1.0 should appear:\n{cmd}"

    def test_reward_is_not_chem_49(self):
        """CHEM 49 is unnamed/unused. Verified from ChemicalNames.catalogue."""
        cmd = _join(_get_harness().inject_reward_caos_cmd(amount=0.5)).lower()
        assert "chem 49" not in cmd, (
            f"inject_reward must NOT use CHEM 49 - use CHEM 204:\n{cmd}"
        )

    def test_reward_is_not_chem_35(self):
        """CHEM 35 is ATP, not reward."""
        cmd = _join(_get_harness().inject_reward_caos_cmd(amount=0.5)).lower()
        assert "chem 35" not in cmd

    def test_no_creature_id_targets_first_norn(self):
        """Without creature_id, should target first norn via enum 4 1 0."""
        cmd = _join(_get_harness().inject_reward_caos_cmd(amount=0.5))
        assert "4 1 0" in cmd, (
            f"Without creature_id, inject_reward should target genus 1 (norns):\n{cmd}"
        )

    def test_with_creature_id_searches_by_name(self):
        """With creature_id, should target a named creature."""
        cmd = _join(_get_harness().inject_reward_caos_cmd(creature_id="NB-001", amount=0.5))
        assert "NB-001" in cmd, f"creature_id 'NB-001' should appear in cmd:\n{cmd}"
        assert "chem 204" in cmd.lower()


class TestInjectPunishmentCmd:
    """inject_punishment_caos_cmd must use CHEM 205, NOT 50 or any other."""

    def test_returns_a_list(self):
        assert isinstance(_get_harness().inject_punishment_caos_cmd(amount=0.5), list)

    def test_punishment_uses_chem_205(self):
        cmd = _join(_get_harness().inject_punishment_caos_cmd(amount=0.5))
        assert "chem 205" in cmd.lower(), (
            f"inject_punishment must use CHEM 205:\n{cmd}"
        )

    def test_punishment_amount(self):
        cmd = _join(_get_harness().inject_punishment_caos_cmd(amount=0.5))
        assert "0.5" in cmd

    def test_punishment_is_not_chem_50(self):
        """CHEM 50 is unnamed/unused. Verified from ChemicalNames.catalogue."""
        cmd = _join(_get_harness().inject_punishment_caos_cmd(amount=0.5)).lower()
        assert "chem 50" not in cmd, (
            f"inject_punishment must NOT use CHEM 50 - use CHEM 205:\n{cmd}"
        )

    def test_no_creature_id_targets_first_norn(self):
        cmd = _join(_get_harness().inject_punishment_caos_cmd(amount=0.5))
        assert "4 1 0" in cmd, (
            f"Without creature_id, inject_punishment should target genus 1 (norns):\n{cmd}"
        )

    def test_with_creature_id(self):
        cmd = _join(_get_harness().inject_punishment_caos_cmd(creature_id="NB-002", amount=0.75))
        assert "NB-002" in cmd
        assert "chem 205" in cmd.lower()


class TestPopulationCmd:
    """population_caos_cmd must query totl for all three genera."""

    def test_returns_a_list(self):
        assert isinstance(_get_harness().population_caos_cmd(), list)

    def test_returns_three_commands(self):
        result = _get_harness().population_caos_cmd()
        assert len(result) == 3, f"population_caos_cmd should return 3 queries, got {len(result)}"

    def test_queries_norns_totl_4_1_0(self):
        cmd = _join(_get_harness().population_caos_cmd())
        assert "totl 4 1 0" in cmd, (
            f"population must query totl 4 1 0 (norns):\n{cmd}"
        )

    def test_queries_grendels_totl_4_2_0(self):
        cmd = _join(_get_harness().population_caos_cmd())
        assert "totl 4 2 0" in cmd, f"population must query totl 4 2 0 (grendels):\n{cmd}"

    def test_queries_ettins_totl_4_3_0(self):
        cmd = _join(_get_harness().population_caos_cmd())
        assert "totl 4 3 0" in cmd, f"population must query totl 4 3 0 (ettins):\n{cmd}"

    def test_all_three_queries_are_distinct(self):
        result = _get_harness().population_caos_cmd()
        assert len(set(result)) == 3, "All three population queries should be distinct"


class TestSaveWorldCmd:
    """save_world_caos_cmd must emit the 'save' CAOS command."""

    def test_returns_a_list(self):
        assert isinstance(_get_harness().save_world_caos_cmd(), list)

    def test_contains_save_command(self):
        cmd = _join(_get_harness().save_world_caos_cmd())
        assert "save" in cmd.lower(), f"save_world must emit 'save' CAOS command:\n{cmd}"

    def test_save_is_the_only_content(self):
        """save_world CAOS should be just 'save', not a complex multi-line script."""
        result = _get_harness().save_world_caos_cmd()
        combined = _join(result).strip().lower()
        assert combined == "save", f"Expected CAOS to be 'save', got: {combined!r}"


class TestFireStimulusCmd:
    """fire_stimulus_caos_cmd must use 'stim writ targ N I' format."""

    def test_returns_a_list(self):
        assert isinstance(_get_harness().fire_stimulus_caos_cmd("NB-001", 3, 1), list)

    def test_stim_writ_format(self):
        cmd = _join(_get_harness().fire_stimulus_caos_cmd("NB-001", 3, 1)).lower()
        assert "stim writ targ" in cmd, (
            f"fire_stimulus must use 'stim writ targ':\n{cmd}"
        )

    def test_stimulus_number_in_cmd(self):
        cmd = _join(_get_harness().fire_stimulus_caos_cmd("NB-001", 7, 1))
        # Verify the stim number appears near the stim writ command
        assert "7" in cmd, f"stim num 7 should appear in cmd:\n{cmd}"

    def test_intensity_in_cmd(self):
        cmd = _join(_get_harness().fire_stimulus_caos_cmd("NB-001", 3, 2))
        assert "2" in cmd, f"intensity 2 should appear in cmd:\n{cmd}"

    def test_creature_id_in_cmd(self):
        cmd = _join(_get_harness().fire_stimulus_caos_cmd("NB-003", 5, 1))
        assert "NB-003" in cmd, f"creature_id should appear in cmd:\n{cmd}"

    def test_targets_family_4(self):
        """Should scope search to creatures (family 4)."""
        cmd = _join(_get_harness().fire_stimulus_caos_cmd("NB-001", 3, 1))
        assert "enum 4" in cmd or "4 0 0" in cmd, (
            f"fire_stimulus should target family 4 (creatures):\n{cmd}"
        )


class TestReadDrivesCmd:
    """read_drives_caos_cmd must query all 20 drives."""

    def test_returns_a_list(self):
        assert isinstance(_get_harness().read_drives_caos_cmd(), list)

    def test_all_20_drive_indices_present(self):
        """The CAOS must read drives 0 through 19."""
        cmd = _join(_get_harness().read_drives_caos_cmd())
        # The harness uses 'drv! targ N' (drv! is the CAOS command for drive value)
        for i in range(20):
            assert str(i) in cmd, (
                f"read_drives_caos_cmd must include drive index {i}:\n{cmd[:200]}..."
            )

    def test_reads_from_creature(self):
        """Should target a creature, not world-level query."""
        cmd = _join(_get_harness().read_drives_caos_cmd()).lower()
        assert "targ" in cmd or "enum" in cmd, (
            f"read_drives should target a creature via enum/targ:\n{cmd}"
        )


class TestSpawnFoodCmd:
    """spawn_food_caos_cmd must use the correct classifier from FOOD_ITEMS."""

    def test_fruit_uses_2_8_0(self):
        cmd = _join(_get_harness().spawn_food_caos_cmd("fruit"))
        assert "2 8 0" in cmd, f"fruit spawn must use (2, 8, 0), got:\n{cmd}"

    def test_cheese_uses_2_11_1(self):
        cmd = _join(_get_harness().spawn_food_caos_cmd("cheese"))
        assert "2 11 1" in cmd, f"cheese spawn must use (2, 11, 1), got:\n{cmd}"

    def test_carrot_uses_2_11_3(self):
        cmd = _join(_get_harness().spawn_food_caos_cmd("carrot"))
        assert "2 11 3" in cmd, f"carrot spawn must use (2, 11, 3), got:\n{cmd}"

    def test_invalid_food_raises(self):
        with pytest.raises((ValueError, KeyError)):
            _get_harness().spawn_food_caos_cmd("pizza")

    def test_fruit_is_not_2_6_0(self):
        """Fruit is genus 8, NOT genus 6. Common confusion."""
        cmd = _join(_get_harness().spawn_food_caos_cmd("fruit"))
        assert "2 6 0" not in cmd, f"Fruit must use (2, 8, 0) not (2, 6, 0):\n{cmd}"


# ===========================================================================
# 3. CLI ARGUMENT PARSING TESTS
# ===========================================================================


class TestCLIArgumentParsing:
    """Verify argparse is correctly configured for all CLI commands."""

    def _parser(self):
        th = _get_harness()
        if hasattr(th, "build_arg_parser"):
            return th.build_arg_parser()
        return th.build_parser()

    def test_spawn_eggs_default_n_is_2(self):
        args = self._parser().parse_args(["spawn-eggs"])
        assert args.n == 2, f"spawn-eggs default n should be 2, got {args.n}"

    def test_spawn_eggs_custom_n_3(self):
        args = self._parser().parse_args(["spawn-eggs", "--n", "3"])
        assert args.n == 3

    def test_teleport_camera_metaroom_arg(self):
        args = self._parser().parse_args(["teleport-camera", "norn-terrarium"])
        assert args.metaroom == "norn-terrarium"

    def test_teleport_camera_all_metarooms_accepted(self):
        """Every metaroom name must be a valid choices value."""
        th = _get_harness()
        parser = self._parser()
        for name in th.METAROOMS.keys():
            # Should not raise SystemExit
            args = parser.parse_args(["teleport-camera", name])
            assert args.metaroom == name

    def test_inject_chem_creature_and_chem_num(self):
        args = self._parser().parse_args(["inject-chem", "NB-001", "204"])
        assert args.creature_id == "NB-001"
        assert args.chem_num == 204

    def test_inject_chem_amount_default_is_0_5(self):
        args = self._parser().parse_args(["inject-chem", "NB-001", "204"])
        assert args.amount == pytest.approx(0.5)

    def test_inject_chem_amount_custom(self):
        args = self._parser().parse_args(["inject-chem", "NB-001", "204", "--amount", "0.75"])
        assert args.amount == pytest.approx(0.75)

    def test_json_flag_is_global(self):
        """--json is a global flag, not per-subcommand."""
        args = self._parser().parse_args(["--json", "save-world"])
        # The flag may be stored as json_output or json depending on implementation
        json_val = getattr(args, "json_output", None) or getattr(args, "json", None)
        assert json_val is True, f"--json flag should be True, got args={vars(args)}"

    def test_json_flag_absent_is_false(self):
        args = self._parser().parse_args(["save-world"])
        json_val = getattr(args, "json_output", False) or getattr(args, "json", False)
        assert json_val is False

    def test_global_port_flag(self):
        args = self._parser().parse_args(["--port", "20002", "save-world"])
        assert args.port == 20002

    def test_default_port_is_20001(self):
        args = self._parser().parse_args(["save-world"])
        assert args.port == 20001

    def test_hatch_all_subcommand(self):
        args = self._parser().parse_args(["hatch-all"])
        assert args.subcmd == "hatch-all"

    def test_kill_grendels_subcommand(self):
        args = self._parser().parse_args(["kill-grendels"])
        assert args.subcmd == "kill-grendels"

    def test_kill_ettins_subcommand(self):
        args = self._parser().parse_args(["kill-ettins"])
        assert args.subcmd == "kill-ettins"

    def test_population_subcommand(self):
        args = self._parser().parse_args(["population"])
        assert args.subcmd == "population"

    def test_save_world_subcommand(self):
        args = self._parser().parse_args(["save-world"])
        assert args.subcmd == "save-world"

    def test_list_creatures_subcommand(self):
        args = self._parser().parse_args(["list-creatures"])
        assert args.subcmd == "list-creatures"

    def test_inject_reward_default_no_creature_id(self):
        args = self._parser().parse_args(["inject-reward"])
        creature_id = getattr(args, "creature_id", None)
        assert creature_id is None, f"inject-reward creature_id should default to None, got {creature_id}"

    def test_inject_reward_with_creature_id(self):
        args = self._parser().parse_args(["inject-reward", "NB-001"])
        assert args.creature_id == "NB-001"

    def test_batch_command(self):
        args = self._parser().parse_args(["batch", "spawn-eggs; hatch-all"])
        # Should accept a batch string
        batch_val = getattr(args, "commands", None) or getattr(args, "batch", None)
        assert batch_val is not None and ("spawn-eggs" in str(batch_val) or "hatch" in str(batch_val))

    def test_fire_stimulus_args(self):
        args = self._parser().parse_args(["fire-stimulus", "NB-001", "5"])
        assert args.creature_id == "NB-001"
        assert args.stim_num == 5


# ===========================================================================
# 4. SAFETY INVARIANT TESTS
# ===========================================================================


class TestSafetyInvariants:
    """Verify critical safety rules encoded in the harness."""

    # ── Egg layer rule ──

    def test_spawn_never_uses_new_colon(self):
        """Project rule: spawn norns ONLY via Norn Egg Layer. No NEW: ever."""
        cmd = _join(_get_harness().spawn_eggs_caos_cmd(n=2)).lower()
        assert "new:" not in cmd, (
            "SAFETY VIOLATION: spawn_eggs used NEW: instead of egg layer (3 3 31)"
        )

    def test_spawn_targets_egg_layer_3_3_31(self):
        cmd = _join(_get_harness().spawn_eggs_caos_cmd(n=1))
        assert "3 3 31" in cmd

    def test_spawn_uses_enum_not_wild_activate(self):
        """activate1 must be scoped inside a 3 3 31 enum, not fired globally."""
        cmd = _join(_get_harness().spawn_eggs_caos_cmd(n=1))
        assert "enum 3 3 31" in cmd, (
            "SAFETY: activate1/mesg writ must be scoped to egg layer enum"
        )

    # ── Genus safety ──

    def test_kill_grendels_genus_is_2_not_1(self):
        """Genus 1 = norn. Genus 2 = grendel. NEVER confuse them."""
        cmd = _join(_get_harness().kill_grendels_caos_cmd())
        assert "4 2 0" in cmd
        assert "4 1 0" not in cmd

    def test_kill_ettins_genus_is_3_not_1(self):
        cmd = _join(_get_harness().kill_ettins_caos_cmd())
        assert "4 3 0" in cmd
        assert "4 1 0" not in cmd

    # ── GAME variable prefix ──

    def test_lnn_prefix_in_auto_name_game_vars(self):
        """All GAME vars must use 'lnn_' prefix per CLAUDE.md directive."""
        cmd = _join(_get_harness().auto_name_all_caos_cmd())
        # Any GAME var mention must use lnn_ prefix
        game_vars = re.findall(r'game\s+"([^"]+)"', cmd, re.IGNORECASE)
        for var in game_vars:
            assert var.startswith("lnn_"), (
                f"GAME var '{var}' must start with 'lnn_' prefix"
            )

    # ── Chemical number safety ──

    def test_reward_chem_constant_is_204(self):
        """Critical: reward = CHEM 204 (from ChemicalNames.catalogue). NOT 49."""
        th = _get_harness()
        if hasattr(th, "REWARD_CHEM"):
            assert th.REWARD_CHEM == 204, f"REWARD_CHEM must be 204, got {th.REWARD_CHEM}"
        # Also verify via generated CAOS
        cmd = _join(th.inject_reward_caos_cmd(amount=0.5))
        assert "204" in cmd

    def test_punishment_chem_constant_is_205(self):
        """Critical: punishment = CHEM 205 (from ChemicalNames.catalogue). NOT 50."""
        th = _get_harness()
        if hasattr(th, "PUNISHMENT_CHEM"):
            assert th.PUNISHMENT_CHEM == 205, (
                f"PUNISHMENT_CHEM must be 205, got {th.PUNISHMENT_CHEM}"
            )
        cmd = _join(th.inject_punishment_caos_cmd(amount=0.5))
        assert "205" in cmd

    def test_all_enum_loops_close_with_next(self):
        """All enum loops must close with 'next'."""
        th = _get_harness()
        checks = [
            ("spawn_eggs", _join(th.spawn_eggs_caos_cmd(n=1))),
            ("hatch_all", _join(th.hatch_all_caos_cmd())),
            ("kill_grendels", _join(th.kill_grendels_caos_cmd())),
            ("kill_ettins", _join(th.kill_ettins_caos_cmd())),
        ]
        for name, cmd in checks:
            assert "next" in cmd.lower(), (
                f"{name} CAOS enum must close with 'next':\n{cmd}"
            )

    def test_activate_all_gadgets_does_not_target_norns(self):
        """Gadget activation must not accidentally enumerate family 4 (creatures)."""
        cmd = _join(_get_harness().activate_all_gadgets_caos_cmd())
        assert "enum 4" not in cmd


# ===========================================================================
# 5. MOCK-BASED CAOS DISPATCH TESTS
# ===========================================================================
#
# Patches caos() in test_harness and verifies the live-dispatch functions
# call it with the correct CAOS strings.
# ===========================================================================


class TestMockedCaosDispatch:
    """Patch caos() and verify dispatch functions call it with correct strings."""

    def test_save_world_calls_caos_save(self):
        th = _get_harness()
        mock_caos = MagicMock(return_value="")
        with patch.object(th, "caos", mock_caos):
            th.save_world()
        all_calls = " ".join(str(c) for c in mock_caos.call_args_list)
        assert "save" in all_calls.lower(), (
            f"save_world must call caos('save'), calls were:\n{all_calls}"
        )

    def test_kill_grendels_calls_with_genus_2(self):
        th = _get_harness()
        mock_caos = MagicMock(return_value="")
        with patch.object(th, "caos", mock_caos):
            th.kill_grendels()
        all_calls = " ".join(str(c) for c in mock_caos.call_args_list)
        assert "4 2 0" in all_calls, (
            f"kill_grendels must call caos with '4 2 0', calls:\n{all_calls}"
        )

    def test_kill_ettins_calls_with_genus_3(self):
        th = _get_harness()
        mock_caos = MagicMock(return_value="")
        with patch.object(th, "caos", mock_caos):
            th.kill_ettins()
        all_calls = " ".join(str(c) for c in mock_caos.call_args_list)
        assert "4 3 0" in all_calls

    def test_inject_reward_calls_chem_204(self):
        th = _get_harness()
        mock_caos = MagicMock(return_value="")
        with patch.object(th, "caos", mock_caos):
            th.inject_reward(amount=0.5)
        all_calls = " ".join(str(c) for c in mock_caos.call_args_list)
        assert "204" in all_calls, (
            f"inject_reward must call caos with CHEM 204, calls:\n{all_calls}"
        )

    def test_inject_punishment_calls_chem_205(self):
        th = _get_harness()
        mock_caos = MagicMock(return_value="")
        with patch.object(th, "caos", mock_caos):
            th.inject_punishment(amount=0.5)
        all_calls = " ".join(str(c) for c in mock_caos.call_args_list)
        assert "205" in all_calls

    def test_spawn_eggs_calls_with_egg_layer(self):
        th = _get_harness()
        mock_caos = MagicMock(return_value="")
        with patch.object(th, "caos", mock_caos):
            th.spawn_eggs(n=1)
        all_calls = " ".join(str(c) for c in mock_caos.call_args_list)
        assert "3 3 31" in all_calls, (
            f"spawn_eggs must call caos targeting egg layer (3 3 31), calls:\n{all_calls}"
        )

    def test_spawn_eggs_n_calls_caos_n_times(self):
        th = _get_harness()
        mock_caos = MagicMock(return_value="")
        with patch.object(th, "caos", mock_caos):
            th.spawn_eggs(n=3)
        # caos() should be called 3 times (once per egg)
        assert mock_caos.call_count == 3, (
            f"spawn_eggs(n=3) should call caos() 3 times, got {mock_caos.call_count}"
        )

    def test_teleport_camera_calls_cmra(self):
        th = _get_harness()
        mock_caos = MagicMock(return_value="")
        with patch.object(th, "caos", mock_caos):
            th.teleport_camera("norn-terrarium")
        all_calls = " ".join(str(c) for c in mock_caos.call_args_list)
        assert "cmra 1190 712 0" in all_calls, (
            f"teleport_camera('norn-terrarium') must call cmra 1190 712 0:\n{all_calls}"
        )

    def test_population_calls_three_totl_queries(self):
        th = _get_harness()
        mock_caos = MagicMock(return_value="0")
        with patch.object(th, "caos", mock_caos):
            th.population()
        all_calls = " ".join(str(c) for c in mock_caos.call_args_list)
        assert "totl 4 1 0" in all_calls, "population must query norns"
        assert "totl 4 2 0" in all_calls, "population must query grendels"
        assert "totl 4 3 0" in all_calls, "population must query ettins"

    def test_hatch_all_calls_pose_3(self):
        th = _get_harness()
        mock_caos = MagicMock(return_value="")
        with patch.object(th, "caos", mock_caos):
            th.hatch_all()
        all_calls = " ".join(str(c) for c in mock_caos.call_args_list)
        assert "pose 3" in all_calls, f"hatch_all must use pose 3:\n{all_calls}"


# ===========================================================================
# 6. INTEGRATION TEST STUBS
# ===========================================================================
#
# Require running engine on TCP 20001. Skipped by default.
# Fill in assertions once the engine is running.
# ===========================================================================


@pytest.mark.integration
class TestIntegrationSpawn:
    """Integration: spawn eggs with a live engine."""

    def test_spawn_one_egg(self):
        """Spawn 1 egg, verify creature count increases by 1."""
        import time
        th = _get_harness()
        initial_norns = th.population().get("norns", 0)
        th.spawn_eggs(n=1)
        time.sleep(2)
        th.hatch_all()
        time.sleep(3)
        final_norns = th.population().get("norns", 0)
        assert final_norns == initial_norns + 1, (
            f"Expected {initial_norns + 1} norns after spawn+hatch, got {final_norns}"
        )

    def test_spawn_and_hatch(self):
        """spawn_and_hatch convenience function works end-to-end."""
        import time
        th = _get_harness()
        initial = th.population().get("norns", 0)
        th.spawn_and_hatch(n=2)
        time.sleep(5)
        final = th.population().get("norns", 0)
        assert final >= initial + 2


@pytest.mark.integration
class TestIntegrationKill:
    """Integration: kill grendels/ettins with a live engine."""

    def test_kill_grendels_reduces_count(self):
        import time
        th = _get_harness()
        initial = th.population().get("grendels", 0)
        if initial == 0:
            pytest.skip("No grendels in world to kill")
        th.kill_grendels()
        time.sleep(1)
        final = th.population().get("grendels", 0)
        assert final < initial

    def test_kill_grendels_does_not_kill_norns(self):
        """Critical safety integration test."""
        import time
        th = _get_harness()
        norn_count_before = th.population().get("norns", 0)
        th.kill_grendels()
        time.sleep(1)
        norn_count_after = th.population().get("norns", 0)
        assert norn_count_after == norn_count_before, (
            "kill_grendels must not kill any norns"
        )


@pytest.mark.integration
class TestIntegrationCamera:
    """Integration: camera teleport with a live engine."""

    def test_teleport_to_norn_terrarium(self):
        th = _get_harness()
        # Should not raise; visual confirmation needed separately
        result = th.teleport_camera("norn-terrarium")
        assert result is not None


@pytest.mark.integration
class TestIntegrationBiochem:
    """Integration: reward/punishment injection and drive reading with a live engine."""

    def test_inject_reward_does_not_raise(self):
        _get_harness().inject_reward(amount=0.5)

    def test_inject_punishment_does_not_raise(self):
        _get_harness().inject_punishment(amount=0.5)

    def test_read_drives_returns_dict_with_20_entries(self):
        th = _get_harness()
        drives = th.read_drives()
        assert isinstance(drives, dict), f"read_drives must return a dict, got {type(drives)}"
        assert len(drives) == 20, f"read_drives must return 20 entries, got {len(drives)}"


@pytest.mark.integration
class TestIntegrationPopulation:
    """Integration: population count with a live engine."""

    def test_population_returns_genus_counts(self):
        th = _get_harness()
        result = th.population()
        assert "norns" in result
        assert "grendels" in result
        assert "ettins" in result
        for key in ("norns", "grendels", "ettins"):
            assert isinstance(result[key], int), (
                f"population[{key!r}] must be int, got {type(result[key])}"
            )


@pytest.mark.integration
class TestIntegrationSaveWorld:
    """Integration: world save with a live engine."""

    def test_save_world_completes(self):
        _get_harness().save_world()  # Should not raise


# ===========================================================================
# Overlay Module Tests
# ===========================================================================


class TestOverlayGeneration:
    """Tests for tools/test_harness_overlay.py CAOS generation."""

    @pytest.fixture(autouse=True)
    def _import_overlay(self):
        overlay_dir = os.path.join(os.path.dirname(__file__), "..", "tools")
        if overlay_dir not in sys.path:
            sys.path.insert(0, overlay_dir)
        from test_harness_overlay import (
            generate_norn_labels_script,
            generate_drive_bars_script,
            generate_world_info_script,
            generate_remove_overlays_script,
        )
        self.gen_labels = generate_norn_labels_script
        self.gen_drives = generate_drive_bars_script
        self.gen_world = generate_world_info_script
        self.gen_remove = generate_remove_overlays_script

    def test_labels_script_is_nonempty_string(self):
        s = self.gen_labels()
        assert isinstance(s, str) and len(s) > 100

    def test_labels_uses_classifier_3_100_0(self):
        s = self.gen_labels()
        assert "3 100 0" in s

    def test_labels_enumerates_norns_family_4_genus_1(self):
        s = self.gen_labels()
        assert "4 1 0" in s

    def test_labels_has_timer_script(self):
        s = self.gen_labels()
        assert "scrp 3 100 0 9" in s.lower() or "scrp 3 100 0 9" in s

    def test_drives_script_returns_string(self):
        """Drive bars are disabled (attr 208 crashes openc2e). Returns comment."""
        s = self.gen_drives()
        assert isinstance(s, str)

    def test_world_info_returns_string(self):
        """World info is disabled (attr 208 crashes openc2e). Returns comment."""
        s = self.gen_world()
        assert isinstance(s, str)

    def test_no_overlay_uses_attr_208(self):
        """attr 208 crashes openc2e -- no overlay should use it."""
        for fn in [self.gen_labels, self.gen_drives, self.gen_world]:
            s = fn()
            assert "attr 208" not in s, f"CRASH HAZARD: attr 208 found in overlay script"
            assert "frat 1" not in s, f"CRASH HAZARD: frat 1 found in overlay script"

    def test_no_overlay_uses_reps(self):
        """reps command doesn't exist in openc2e."""
        s = self.gen_remove()
        assert "reps" not in s.lower(), "reps crashes openc2e -- use kill targ instead"

    def test_remove_kills_all_overlay_classifiers(self):
        s = self.gen_remove()
        assert "3 100 0" in s
        assert "3 101 0" in s
        assert "3 102 0" in s
        assert "kill" in s.lower()


# ===========================================================================
# Panel Module Tests
# ===========================================================================


class TestPanelGeneration:
    """Tests for tools/test_harness_caos.py CAOS generation."""

    @pytest.fixture(autouse=True)
    def _import_panel(self):
        panel_dir = os.path.join(os.path.dirname(__file__), "..", "tools")
        if panel_dir not in sys.path:
            sys.path.insert(0, panel_dir)
        from test_harness_caos import (
            generate_panel_script,
            generate_panel_handlers_script,
        )
        self.gen_panel = generate_panel_script
        self.gen_handlers = generate_panel_handlers_script

    def test_panel_script_is_nonempty(self):
        s = self.gen_panel()
        assert isinstance(s, str) and len(s) > 500

    def test_panel_uses_classifier_3_103(self):
        s = self.gen_panel()
        assert "3 103" in s

    def test_panel_creates_multiple_button_agents(self):
        s = self.gen_panel().lower()
        assert s.count("new: simp") >= 10, "Expected at least 10 button agents"

    def test_handlers_is_nonempty(self):
        s = self.gen_handlers()
        assert isinstance(s, str) and len(s) > 500

    def test_handlers_has_scrp_blocks(self):
        s = self.gen_handlers()
        assert s.count("scrp 3 103") >= 10, "Expected at least 10 handler scripts"

    def test_handlers_all_have_endm(self):
        s = self.gen_handlers()
        scrp_count = s.lower().count("scrp")
        endm_count = s.lower().count("endm")
        assert scrp_count == endm_count, f"Mismatched scrp({scrp_count})/endm({endm_count})"

    # Safety tests on panel CAOS
    def test_panel_egg_spawning_uses_egg_layer(self):
        s = self.gen_handlers()
        assert "3 3 31" in s, "Must use Egg Layer classifier"

    def test_panel_kill_grendels_uses_genus_2(self):
        s = self.gen_handlers()
        assert "4 2 0" in s, "Kill grendels must target genus 2"

    def test_panel_kill_does_not_target_norns(self):
        s = self.gen_handlers()
        # Find kill commands - they should not be in context of 4 1 0
        lines = s.split("\n")
        for i, line in enumerate(lines):
            if "kill targ" in line.lower():
                # Check surrounding context (5 lines before) for enum 4 1 0
                context = "\n".join(lines[max(0, i-5):i+1])
                assert "enum 4 1 0" not in context, "kill must not target norns (4 1 0)"

    def test_panel_reward_uses_chem_204(self):
        s = self.gen_handlers()
        assert "chem 204" in s, "Reward must use CHEM 204"

    def test_panel_punishment_uses_chem_205(self):
        s = self.gen_handlers()
        assert "chem 205" in s, "Punishment must use CHEM 205"

    def test_panel_metaroom_coords_correct(self):
        s = self.gen_handlers()
        assert "cmra 1190 712" in s, "Norn Terrarium coords wrong"

    def test_panel_no_attr_208(self):
        """attr 208 crashes openc2e -- panel must not use it in executable CAOS."""
        s = self.gen_panel()
        for line in s.split("\n"):
            stripped = line.strip()
            if stripped.startswith("*"):  # CAOS comment
                continue
            assert "attr 208" not in stripped, f"CRASH HAZARD: attr 208 in: {stripped}"

    def test_panel_no_endm_outside_scrp(self):
        """endm outside scrp block kills injection context."""
        s = self.gen_panel()
        # endm should only appear inside handler scripts, not in creation script
        assert "endm" not in s.lower(), "endm in panel creation script will abort injection"

    def test_panel_new_simp_has_plane(self):
        """new: simp without plane parameter silently fails in openc2e."""
        s = self.gen_panel()
        import re
        # Every new: simp should have 7 args (family genus species sprite first num plane)
        for m in re.finditer(r'new: simp (\d+ \d+ \d+ "[^"]+" \d+ \d+)(.*)', s):
            rest = m.group(2).strip()
            # The next token after num_images should be a number (plane), not a command
            assert rest and rest.split()[0].isdigit(), \
                f"new: simp missing plane parameter: {m.group(0)[:60]}"

    def test_panel_handlers_no_lv_vars(self):
        """lv00/lv01 are invalid in scrp handler context -- must use va vars."""
        s = self.gen_handlers()
        for line in s.split("\n"):
            stripped = line.strip()
            if stripped.startswith("*"):  # CAOS comment
                continue
            assert "lv0" not in stripped.lower(), \
                f"lv vars invalid in script store: {stripped}"

    def test_panel_cleans_existing_before_creating(self):
        s = self.gen_panel().lower()
        # Should kill existing panel agents before creating new ones
        kill_pos = s.find("kill")
        new_pos = s.find("new:")
        assert kill_pos < new_pos, "Should remove existing panel before creating new"


# ===========================================================================
# CLI Integration for Overlay/Panel
# ===========================================================================


class TestCLIOverlayPanelParsing:
    """Test that overlay/panel subcommands parse correctly."""

    @pytest.fixture(autouse=True)
    def _parser(self):
        self.parser = _get_harness().build_parser()

    def test_inject_overlays_parses(self):
        args = self.parser.parse_args(["inject-overlays"])
        assert args.subcmd == "inject-overlays"

    def test_remove_overlays_parses(self):
        args = self.parser.parse_args(["remove-overlays"])
        assert args.subcmd == "remove-overlays"

    def test_inject_labels_parses(self):
        args = self.parser.parse_args(["inject-labels"])
        assert args.subcmd == "inject-labels"

    def test_inject_drive_bars_parses(self):
        args = self.parser.parse_args(["inject-drive-bars"])
        assert args.subcmd == "inject-drive-bars"

    def test_inject_world_info_parses(self):
        args = self.parser.parse_args(["inject-world-info"])
        assert args.subcmd == "inject-world-info"

    def test_inject_panel_parses(self):
        args = self.parser.parse_args(["inject-panel"])
        assert args.subcmd == "inject-panel"

    def test_remove_panel_parses(self):
        args = self.parser.parse_args(["remove-panel"])
        assert args.subcmd == "remove-panel"

    def test_prep_world_parses(self):
        args = self.parser.parse_args(["prep-world"])
        assert args.subcmd == "prep-world"


# ===========================================================================
# Entry point (also runnable without pytest)
# ===========================================================================

if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "-m", "not integration"],
        check=False,
    )
    sys.exit(result.returncode)
