"""
Check manually staged source files required for exact release reproduction.

The pipeline downloads/reuses Census TIGER/Line boundary inputs automatically,
but selected public context layers are intentionally staged manually because
stable automated download access is not guaranteed. This preflight keeps the
full runner from creating partial outputs when those source files are missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RequiredSource:
    """One local source file required for exact release reproduction."""

    name: str
    relative_path: str
    source_url: str
    documentation: str
    requirement: str

    @property
    def path(self) -> Path:
        return PROJECT_ROOT / self.relative_path


REQUIRED_SOURCES = [
    RequiredSource(
        name="HUD Opportunity Zones",
        relative_path="data/raw/hud_opportunity_zones/hud_opportunity_zones_tx.geojson",
        source_url="https://hudgis-hud.opendata.arcgis.com/datasets/HUD::opportunity-zones/about",
        documentation="docs/data_sources.md; docs/download_plan.md",
        requirement="context layer required for exact release reproduction",
    ),
    RequiredSource(
        name="Texas Unified School Districts",
        relative_path="data/raw/texas_school_districts/tl_2025_48_unsd.zip",
        source_url="https://www2.census.gov/geo/tiger/TIGER2025/UNSD/tl_2025_48_unsd.zip",
        documentation="docs/data_sources.md; docs/download_plan.md",
        requirement="neutral context layer required for exact release reproduction",
    ),
]


def build_rows() -> list[dict[str, str]]:
    """Build source check rows for console output and missing-path reporting."""
    rows = []
    for source in REQUIRED_SOURCES:
        found = source.path.exists()
        rows.append(
            {
                "source_name": source.name,
                "required_local_path": str(source.path),
                "status": "found" if found else "missing",
                "source_url": source.source_url,
                "documentation": source.documentation,
                "requirement": source.requirement,
            }
        )
    return rows


def print_rows(rows: list[dict[str, str]]) -> None:
    """Print a compact source preflight report."""
    print("Source preflight check")
    for row in rows:
        print(f"- Source: {row['source_name']}")
        print(f"  Required local path: {row['required_local_path']}")
        print(f"  Status: {row['status']}")
        print(f"  Requirement: {row['requirement']}")
        if row["status"] == "missing":
            print(f"  Source URL: {row['source_url']}")
            print(f"  Documentation: {row['documentation']}")


def main() -> int:
    """Run source preflight and return non-zero when required files are missing."""
    rows = build_rows()
    print_rows(rows)
    missing_paths = [row["required_local_path"] for row in rows if row["status"] == "missing"]
    if missing_paths:
        print()
        print("Required local source files are missing.")
        print("See docs/data_sources.md and docs/download_plan.md.")
        print("Missing paths:")
        for path in missing_paths:
            print(f"- {path}")
        return 1

    print()
    print("All required local source files were found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
