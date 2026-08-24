"""Export a trained INDRA sensor-only model through the existing C generator."""

import argparse
import json
from pathlib import Path

from ml import convert_to_c


def _write_metadata_header(
    output_path: Path,
    feature_names: list[str],
    thresholds: dict[str, float],
    schema_version: str,
    schema_sha256: str,
) -> None:
    lines = [
        "/**",
        " * model_metadata.h - Auto-generated INDRA sensor-only metadata",
        " */",
        "",
        "#ifndef MODEL_METADATA_H",
        "#define MODEL_METADATA_H",
        "",
        f'#define MODEL_SCHEMA_VERSION "{schema_version}"',
        f'#define MODEL_SCHEMA_SHA256 "{schema_sha256}"',
        "",
        f"static const char *FEATURE_NAMES_METADATA[{len(feature_names)}] = {{",
    ]
    lines.extend(f'    "{name}",' for name in feature_names)
    lines.extend(
        [
            "};",
            "",
            "static const char *HAZARD_CLASS_NAMES[4] = {",
            '    "wildfire",',
            '    "flood",',
            '    "storm",',
            '    "air_quality",',
            "};",
            "",
            "static const float ALERT_THRESHOLDS[4] = {",
        ]
    )
    lines.extend(
        f"    {thresholds[name]:.9f}f,  // {name}"
        for name in convert_to_c.HAZARD_CLASSES
    )
    lines.extend(["};", "", "#endif // MODEL_METADATA_H", ""])
    output_path.write_text("\n".join(lines))


def export(model_dir: Path, output_path: Path, allow_not_ready: bool = False) -> None:
    manifest = json.loads((model_dir / "model_manifest.json").read_text())
    if manifest.get("deployment_status") == "NOT_READY" and not allow_not_ready:
        raise ValueError(
            "Model manifest is NOT_READY. Refusing firmware export; use "
            "--allow-not-ready only for integration testing."
        )
    missing_heads = [
        hazard
        for hazard in convert_to_c.HAZARD_CLASSES
        if not (model_dir / f"xgboost_{hazard}.json").exists()
    ]
    if missing_heads:
        raise ValueError(f"Cannot export missing model heads: {missing_heads}")

    normalization = json.loads((model_dir / "normalization.json").read_text())
    feature_names = normalization["feature_names"]
    if len(feature_names) != 14:
        raise ValueError(f"ESP firmware contract requires 14 features, got {len(feature_names)}")
    convert_to_c.FEATURE_NAMES = feature_names
    convert_to_c.NUM_FEATURES = len(feature_names)

    trees = convert_to_c.load_model_trees(str(model_dir), convert_to_c.MAX_TREES_PER_CLASS)
    base_scores = convert_to_c.load_model_base_scores(str(model_dir))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    convert_to_c.generate_model_header(trees, normalization, str(output_path), base_scores)
    convert_to_c.generate_normalization_header(normalization, str(output_path))

    schema_version = normalization["schema_version"]
    schema_sha256 = normalization["schema_sha256"]
    header = output_path.read_text()
    marker = "#define MODEL_DATA_H\n"
    schema_defines = (
        f'{marker}\n#define MODEL_SCHEMA_VERSION "{schema_version}"\n'
        f'#define MODEL_SCHEMA_SHA256 "{schema_sha256}"\n'
    )
    if marker not in header:
        raise ValueError("Generated header does not contain the expected include guard")
    output_path.write_text(header.replace(marker, schema_defines, 1))

    thresholds = json.loads((model_dir / "thresholds.json").read_text())
    _write_metadata_header(
        output_path.with_name("model_metadata.h"),
        feature_names,
        thresholds,
        schema_version,
        schema_sha256,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    export(args.model, args.output, args.allow_not_ready)
    print(f"Generated {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

