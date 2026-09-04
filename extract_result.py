import json
from datetime import datetime
from pathlib import Path

from pyswmm import Output
from swmm.toolkit.shared_enum import LinkAttribute, NodeAttribute

ROOT = Path(__file__).resolve().parent
OUTPUT_FILE = ROOT / "swmm" / "flood_output.out"


def _normalize_timestamp(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def extract_swmm_results(output_file=OUTPUT_FILE):
    output_path = Path(output_file)
    if not output_path.is_file():
        raise FileNotFoundError(f"SWMM output file was not found: {output_path}")

    results = {"nodes": {}, "links": {}}

    with Output(str(output_path)) as out:
        for node in out.nodes:
            node_entry = {}
            for attribute in (
                NodeAttribute.INVERT_DEPTH,
                NodeAttribute.HYDRAULIC_HEAD,
                NodeAttribute.PONDED_VOLUME,
                NodeAttribute.FLOODING_LOSSES,
            ):
                try:
                    values = out.node_series(node, attribute)
                except Exception:
                    continue
                if not values:
                    continue
                node_entry[attribute.name.lower()] = {
                    _normalize_timestamp(ts): float(value)
                    for ts, value in values.items()
                }
            results["nodes"][node] = node_entry

        for link in out.links:
            link_entry = {}
            for attribute in (
                LinkAttribute.FLOW_RATE,
                LinkAttribute.FLOW_DEPTH,
                LinkAttribute.FLOW_VELOCITY,
                LinkAttribute.CAPACITY,
            ):
                try:
                    values = out.link_series(link, attribute)
                except Exception:
                    continue
                if not values:
                    continue
                link_entry[attribute.name.lower()] = {
                    _normalize_timestamp(ts): float(value)
                    for ts, value in values.items()
                }
            results["links"][link] = link_entry

    return results


def main():
    print("=" * 60)
    print("URBAN FLOOD SIMULATION RESULTS")
    print("=" * 60)

    results = extract_swmm_results(OUTPUT_FILE)

    for node, metrics in results["nodes"].items():
        print(f"\nNODE {node}")
        for attr_name, values in metrics.items():
            if not values:
                continue
            max_value = max(values.values())
            print(f"  {attr_name}: max={max_value:.4f}")

    for link, metrics in results["links"].items():
        print(f"\nLINK {link}")
        for attr_name, values in metrics.items():
            if not values:
                continue
            max_value = max(values.values())
            print(f"  {attr_name}: max={max_value:.4f}")

    print("\n" + "=" * 60)
    print("RESULT EXTRACTION SUCCESSFUL")
    print("=" * 60)


if __name__ == "__main__":
    main()