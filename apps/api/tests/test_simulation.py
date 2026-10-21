"""Seeded telemetry generation: determinism, safety markers, structure."""

import ipaddress

from app.domain.scenarios.loader import SCENARIO_ID, load_scenario
from app.domain.simulation.engine import generate_telemetry
from app.shared.vocab import RESERVED_NETWORKS, STAGE_IDS

SCENARIO = load_scenario(SCENARIO_ID)
RESERVED = [ipaddress.ip_network(n) for n in RESERVED_NETWORKS]


def test_same_seed_produces_identical_telemetry() -> None:
    a = generate_telemetry(SCENARIO, "run_a", 1337)
    b = generate_telemetry(SCENARIO, "run_a", 1337)
    assert [e.model_dump() for e in a] == [e.model_dump() for e in b]


def test_event_ids_deterministic_across_run_ids() -> None:
    a = generate_telemetry(SCENARIO, "run_a", 1337)
    b = generate_telemetry(SCENARIO, "run_b", 1337)
    assert [e.id for e in a] == [e.id for e in b]


def test_different_seed_changes_telemetry() -> None:
    a = generate_telemetry(SCENARIO, "run_a", 1337)
    b = generate_telemetry(SCENARIO, "run_a", 1338)
    assert [e.model_dump() for e in a] != [e.model_dump() for e in b]


def test_every_event_is_synthetic_and_in_reserved_ranges() -> None:
    events = generate_telemetry(SCENARIO, "run_a", 1337)
    assert events, "simulator must produce events"
    for event in events:
        assert event.synthetic is True
        ip = ipaddress.ip_address(event.src_ip)
        assert any(ip in network for network in RESERVED), f"{event.src_ip} not reserved"


def test_events_cover_all_stages_with_expected_and_background() -> None:
    events = generate_telemetry(SCENARIO, "run_a", 1337)
    stages = {e.stage_id for e in events}
    assert stages == set(STAGE_IDS)
    for stage_id in ("S1", "S2", "S3", "S4", "S5", "S6", "S7"):
        stage_events = [e for e in events if e.stage_id == stage_id]
        assert any(e.expected for e in stage_events), f"{stage_id} lacks expected events"
    assert any(not e.expected for e in events), "simulator must include background noise"


def test_timestamps_are_utc_and_ordered() -> None:
    events = generate_telemetry(SCENARIO, "run_a", 1337)
    timestamps = [e.timestamp for e in events]
    assert timestamps == sorted(timestamps)
    assert all(e.timestamp.tzinfo is not None for e in events)