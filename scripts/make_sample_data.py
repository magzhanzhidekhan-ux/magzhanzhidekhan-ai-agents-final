import json
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(2026)
END = date(2026, 11, 9)
DAYS = 90
MEAN = {"SKU-1001": 3.0, "SKU-1002": 2.0, "SKU-1003": 1.2, "SKU-2001": 4.0,
        "SKU-2002": 9.0, "SKU-3002": 1.5}          # SKU-3001 has no sales on purpose

sales = {}
for sku, mean in MEAN.items():
    sales[sku] = [{"date": (END - timedelta(days=DAYS - 1 - i)).isoformat(),
                   "units": max(0, round(random.gauss(mean, mean * 0.3)))}
                  for i in range(DAYS)]

out = {"description": "Fictional daily sales, generated with a fixed seed.", "sales": sales}
Path("data/sales.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("wrote data/sales.json")