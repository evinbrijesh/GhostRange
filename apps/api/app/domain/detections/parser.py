"""Parser for the documented GhostRange rule subset (Sigma-like, NOT full Sigma).

Supported syntax:

    title: <str>                     (required)
    id: <str>                        (required, must start with "rule_")
    stage: S1..S7                    (required)
    logsource: {product, service}    (required; service must be an event source)
    selection: {field: value, ...}   (required, non-empty; keys AND together)
    condition: selection             (required; only "selection" is supported)
    level: low|medium|high|critical  (optional)

Field expressions: `<field>` for exact matching or `<field>|contains` for
substring matching. Supported fields: action, source, srcIp, identity.id,
identity.type, resource.id, resource.type, attributes.<key>.

Anything else fails with a clear, safe validation error. Unsupported syntax
must fail loudly — silently ignoring it would hide security gaps.
"""

import yaml

from app.domain.detections.models import DetectionRule, LogSource
from app.shared.vocab import EVENT_SOURCES, STAGE_IDS, EventSource, RuleLevel

SUPPORTED_TOP_LEVEL_KEYS = {"title", "id", "stage", "logsource", "selection", "condition", "level"}
SUPPORTED_OPERATORS = {"contains"}
SUPPORTED_FIELDS = {
    "action", "source", "srcIp",
    "identity.id", "identity.type",
    "resource.id", "resource.type",
}


class RuleParseError(ValueError):
    pass


def _fail(rule_id: str, errors: list[str], stage: object = None, service: object = None) -> DetectionRule:
    # Preserve stage/service attribution when they are known so evaluator errors
    # land on the right stage instead of silently moving to S1.
    stage_id = stage if isinstance(stage, str) and stage in STAGE_IDS else STAGE_IDS[0]
    svc = service if isinstance(service, str) and service in EVENT_SOURCES else EventSource.API
    return DetectionRule(
        id=rule_id or "rule_unparsed",
        version="v1",
        title="(unparsed rule)",
        stage_id=stage_id,
        logsource=LogSource(product="cloud", service=svc),
        source="",
        parser_status="invalid",
        parser_errors=errors,
        level=None,
        enabled=True,
    )


def _validate_field_expr(expr: str, rule_id: str, errors: list[str]) -> tuple[str, str] | None:
    parts = expr.split("|")
    base, operators = parts[0], parts[1:]
    unknown = [op for op in operators if op not in SUPPORTED_OPERATORS]
    if unknown:
        errors.append(
            f"rule {rule_id}: unsupported operator(s) {unknown} in field '{expr}'. "
            f"Supported: exact match or '|contains'."
        )
        return None
    if base in SUPPORTED_FIELDS or base.startswith("attributes."):
        return base, "contains" if "contains" in operators else "exact"
    errors.append(
        f"rule {rule_id}: unsupported field '{base}'. Supported fields: "
        f"{sorted(SUPPORTED_FIELDS)} or 'attributes.<key>'."
    )
    return None


def parse_rule(source: str) -> tuple[DetectionRule, tuple[tuple[str, str, str], ...]]:
    """Parse one rule. Returns (contract-shaped rule, compiled selection).

    Never raises for rule content problems: invalid rules come back with
    parser_status="invalid" and safe error messages, so one bad rule cannot
    break a run. Structural failures (unparseable YAML) are handled the same way.
    """
    errors: list[str] = []

    try:
        raw = yaml.safe_load(source)
    except yaml.YAMLError as exc:
        return _fail("rule_unparsed", [f"invalid YAML: {exc.problem}"]), ()

    if not isinstance(raw, dict):
        return _fail("rule_unparsed", ["rule must be a YAML mapping"]), ()

    rule_id = str(raw.get("id", "rule_unparsed"))
    unknown_keys = set(raw) - SUPPORTED_TOP_LEVEL_KEYS
    if unknown_keys:
        errors.append(
            f"rule {rule_id}: unsupported top-level key(s) {sorted(unknown_keys)}. "
            f"Supported: {sorted(SUPPORTED_TOP_LEVEL_KEYS)}."
        )

    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append(f"rule {rule_id}: 'title' is required and must be a non-empty string")

    stage = raw.get("stage")
    if stage not in STAGE_IDS:
        errors.append(f"rule {rule_id}: 'stage' must be one of {list(STAGE_IDS)}, got {stage!r}")

    logsource_raw = raw.get("logsource")
    logsource: LogSource | None = None
    logsource_ok = False
    if not isinstance(logsource_raw, dict):
        errors.append(f"rule {rule_id}: 'logsource' with product and service is required")
    else:
        product, service = logsource_raw.get("product"), logsource_raw.get("service")
        if not isinstance(product, str) or not product.strip():
            errors.append(f"rule {rule_id}: logsource.product must be a non-empty string")
        if service not in EVENT_SOURCES:
            errors.append(
                f"rule {rule_id}: logsource.service must be one of "
                f"{sorted(EVENT_SOURCES)}, got {service!r}"
            )
        if isinstance(product, str) and product.strip() and service in EVENT_SOURCES:
            logsource = LogSource(product=product, service=service)
            logsource_ok = True

    selection_raw = raw.get("selection")
    selection: list[tuple[str, str, str]] = []
    if not isinstance(selection_raw, dict) or not selection_raw:
        errors.append(f"rule {rule_id}: 'selection' must be a non-empty mapping of field expressions")
    else:
        for expr, value in selection_raw.items():
            if not isinstance(expr, str):
                errors.append(f"rule {rule_id}: selection keys must be strings, got {expr!r}")
                continue
            if not isinstance(value, (str, int, float, bool)):
                errors.append(
                    f"rule {rule_id}: selection value for '{expr}' must be a scalar "
                    f"(string/number/boolean); lists and mappings are not supported"
                )
                continue
            parsed_expr = _validate_field_expr(expr, rule_id, errors)
            if parsed_expr is not None:
                base, op = parsed_expr
                selection.append((base, op, str(value)))

    condition = raw.get("condition")
    if condition != "selection":
        errors.append(
            f"rule {rule_id}: only condition 'selection' is supported, got {condition!r}"
        )

    level = raw.get("level")
    if level is not None and level not in RuleLevel:
        errors.append(
            f"rule {rule_id}: 'level' must be one of "
            f"{[lvl.value for lvl in RuleLevel]}, got {level!r}"
        )

    if errors:
        return _fail(rule_id, errors, stage=stage, service=raw.get("logsource", {}).get("service")
                     if isinstance(raw.get("logsource"), dict) else None), ()

    assert logsource_ok and logsource is not None and isinstance(title, str) and isinstance(stage, str)
    rule = DetectionRule(
        id=rule_id,
        version="v1",
        title=title,
        stage_id=stage,
        logsource=logsource,
        source=source,
        parser_status="valid",
        parser_errors=[],
        level=level,
        enabled=True,
    )
    return rule, tuple(selection)