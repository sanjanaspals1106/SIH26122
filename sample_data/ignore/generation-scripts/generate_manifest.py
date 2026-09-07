import os
import hashlib
import json

base = r"D:\SIH26122\sample_data"
manifest = {
    "project": "SIH26122",
    "title": "Intelligent Construction Progress Data Capture & Schedule-Linking Benchmark Dataset",
    "canonical_activities_count": 45,
    "disciplines": {
        "Civil": 8,
        "Piping": 10,
        "Static/Rotating Equipment": 7,
        "Electrical": 8,
        "Instrumentation": 7,
        "HSE": 5
    },
    "reporting_dates": [
        "2026-08-11", "2026-08-12", "2026-08-13", "2026-08-14",
        "2026-08-15", "2026-08-18", "2026-08-19", "2026-08-20",
        "2026-08-21", "2026-08-22"
    ],
    "file_counts_by_category": {},
    "files": []
}

cat_counts = {}
for root, dirs, files in os.walk(base):
    for f in sorted(files):
        if f in ["dataset_manifest.json", "DATASET_README.md"]:
            continue
        fp = os.path.join(root, f)
        rel_p = os.path.relpath(fp, base).replace("\\", "/")
        category = rel_p.split("/")[0]
        cat_counts[category] = cat_counts.get(category, 0) + 1
        size = os.path.getsize(fp)
        with open(fp, "rb") as fh:
            h = hashlib.sha256(fh.read()).hexdigest()
        manifest["files"].append({
            "path": rel_p,
            "category": category,
            "size_bytes": size,
            "sha256": h
        })

manifest["file_counts_by_category"] = cat_counts

out_p = os.path.join(base, "dataset_manifest.json")
with open(out_p, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
print("Generated dataset_manifest.json with", len(manifest["files"]), "files tracked.")
