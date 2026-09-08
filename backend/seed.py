import json
import sys
from backend.shared.seed import load_canonical_sample_data


def main() -> int:
    """CLI runner for canonical sample data seeding."""
    print("Running SIH26122 Canonical Sample Data Loader...")
    result = load_canonical_sample_data()

    print(json.dumps(result, indent=2))

    if result.get("status") == "BLOCKED":
        print(f"\n[NOTICE] Seeding BLOCKED: {result.get('reason')}")
        return 0

    if result.get("status") == "SUCCESS":
        print("\n[SUCCESS] Canonical sample data successfully seeded.")
        return 0

    print(f"\n[ERROR] Seeding failed with status: {result.get('status')}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
