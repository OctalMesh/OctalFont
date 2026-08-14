"""DesignSpace document generator."""

from __future__ import annotations

from pathlib import Path

try:
    from fontTools.designspaceLib import (
        AxisDescriptor,
        DesignSpaceDocument,
        InstanceDescriptor,
        SourceDescriptor,
    )
except ImportError:
    raise SystemExit("[svg_to_ufo] Missing dependency: fonttools\nRun: octalfont env --setup")

from svg_to_ufo.config import WEIGHT_MAP


def build_designspace(
    family_dir: Path,
    ufo_paths: dict[str, Path],
    metrics: dict,
    dry_run: bool = False,
    force: bool = False,
) -> Path:
    """Generate a DesignSpace file at <family_dir>/<FamilyName>.designspace.

    Single-master families get a degenerate wght axis (min == default == max)
    so fontmake accepts the file. Multi-master families get a full variable
    axis spanning all supplied weights. Each source receives a matching
    Instance so gftools builder can produce static TTFs alongside the
    variable font.

    Args:
        family_dir: Absolute path to the family source directory.
        ufo_paths: Mapping of weight_name -> ufo_path for all built masters.
        metrics: Parsed metrics.yaml contents.
        dry_run: When True, print what would happen without writing.
        force: When True, overwrite an existing .designspace file.

    Returns:
        The path to the .designspace file.
    """

    family_name = metrics.get("family_name", family_dir.name)
    ds_path = family_dir / f"{family_dir.name}.designspace"

    if dry_run:
        action = (
            "overwrite"
            if (force or not ds_path.exists())
            else "skip – already exists (use --force-designspace to overwrite)"
        )

        print(
            f"  DesignSpace would {action} -> "
            f"{ds_path.relative_to(family_dir.parent.parent)}"
        )

        return ds_path

    if ds_path.exists() and not force:
        print(
            "  DesignSpace already exists, skipping "
            "(use --force-designspace to regenerate)."
        )

        return ds_path

    designspace_doc = DesignSpaceDocument()

    if len(ufo_paths) > 1:
        # Variable: build a real wght axis across all supplied masters.
        weight_axis = AxisDescriptor()
        weight_axis.tag = "wght"
        weight_axis.name = "Weight"
        weight_axis.minimum = min(WEIGHT_MAP.get(w, 400) for w in ufo_paths)
        weight_axis.default = WEIGHT_MAP.get("Regular", 400)
        weight_axis.maximum = max(WEIGHT_MAP.get(w, 400) for w in ufo_paths)

        designspace_doc.addAxis(weight_axis)
    else:
        # Static: add a degenerate wght axis so fontmake accepts the file.
        weight_axis = AxisDescriptor()
        weight_axis.tag = "wght"
        weight_axis.name = "Weight"
        weight_axis.minimum = weight_axis.default = weight_axis.maximum = 400

        designspace_doc.addAxis(weight_axis)

    for weight_name, ufo_path in ufo_paths.items():
        weight_value = WEIGHT_MAP.get(weight_name, 400)

        source_descriptor = SourceDescriptor()
        source_descriptor.filename = str(ufo_path.relative_to(family_dir))
        source_descriptor.familyName = family_name
        source_descriptor.styleName = weight_name
        source_descriptor.location = {"Weight": weight_value}
        source_descriptor.copyInfo = weight_name == "Regular" or len(ufo_paths) == 1

        designspace_doc.addSource(source_descriptor)

        instance_descriptor = InstanceDescriptor()
        instance_descriptor.familyName = family_name
        instance_descriptor.styleName = weight_name
        instance_descriptor.name = f"{family_name}-{weight_name}"
        instance_descriptor.location = {"Weight": weight_value}
        instance_descriptor.filename = f"instances/{family_dir.name}-{weight_name}.ufo"

        designspace_doc.addInstance(instance_descriptor)

    designspace_doc.write(str(ds_path))
    print(f"  DesignSpace written -> {ds_path.relative_to(family_dir.parent.parent)}")

    return ds_path
