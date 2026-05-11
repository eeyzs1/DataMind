import os
import sys
from pathlib import Path

import pandas as pd

KAGGLE_DATASETS = {
    "olist_orders": "olist_orders_dataset.csv",
    "olist_payments": "olist_order_payments_dataset.csv",
    "olist_customers": "olist_customers_dataset.csv",
    "olist_products": "olist_products_dataset.csv",
    "olist_reviews": "olist_order_reviews_dataset.csv",
}

GITHUB_MIRROR = {
    "olist_orders": "https://raw.githubusercontent.com/olist/workbook/master/datasets/olist_orders_dataset.csv",
    "olist_payments": "https://raw.githubusercontent.com/olist/workbook/master/datasets/olist_order_payments_dataset.csv",
    "olist_customers": "https://raw.githubusercontent.com/olist/workbook/master/datasets/olist_customers_dataset.csv",
    "olist_products": "https://raw.githubusercontent.com/olist/workbook/master/datasets/olist_products_dataset.csv",
    "olist_reviews": "https://raw.githubusercontent.com/olist/workbook/master/datasets/olist_order_reviews_dataset.csv",
}

SAMPLE_DATA = {
    "olist_orders": {
        "columns": ["order_id", "customer_id", "order_status", "order_purchase_timestamp",
                     "order_approved_at", "order_delivered_carrier_date",
                     "order_delivered_customer_date", "order_estimated_delivery_date"],
        "rows": [
            ["ORD001", "CUST001", "delivered", "2024-01-15 10:30:00", "2024-01-15 10:35:00",
             "2024-01-16 08:00:00", "2024-01-20 14:00:00", "2024-01-25 00:00:00"],
            ["ORD002", "CUST002", "shipped", "2024-01-16 14:20:00", "2024-01-16 14:25:00",
             "2024-01-17 09:00:00", None, "2024-01-26 00:00:00"],
            ["ORD003", "CUST003", "delivered", "2024-01-17 09:15:00", "2024-01-17 09:20:00",
             "2024-01-18 10:00:00", "2024-01-22 11:00:00", "2024-01-27 00:00:00"],
            ["ORD004", "CUST001", "canceled", "2024-01-18 16:45:00", None, None, None, "2024-01-28 00:00:00"],
            ["ORD005", "CUST004", "delivered", "2024-01-20 11:00:00", "2024-01-20 11:05:00",
             "2024-01-21 08:30:00", "2024-01-25 16:00:00", "2024-01-30 00:00:00"],
        ]
    },
    "olist_payments": {
        "columns": ["order_id", "payment_sequential", "payment_type",
                     "payment_installments", "payment_value"],
        "rows": [
            ["ORD001", 1, "credit_card", 3, 150.50],
            ["ORD002", 1, "boleto", 1, 220.00],
            ["ORD003", 1, "credit_card", 1, 89.90],
            ["ORD003", 2, "voucher", 1, 10.10],
            ["ORD005", 1, "debit_card", 1, 340.75],
        ]
    },
    "olist_customers": {
        "columns": ["customer_id", "customer_unique_id", "customer_zip_code_prefix",
                     "customer_city", "customer_state"],
        "rows": [
            ["CUST001", "UNIQ001", "01001", "Sao Paulo", "SP"],
            ["CUST002", "UNIQ002", "20040", "Rio de Janeiro", "RJ"],
            ["CUST003", "UNIQ003", "30130", "Belo Horizonte", "MG"],
            ["CUST004", "UNIQ004", "40010", "Salvador", "BA"],
        ]
    },
    "olist_products": {
        "columns": ["product_id", "product_category_name", "product_name_lenght",
                     "product_description_lenght", "product_photos_qty",
                     "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"],
        "rows": [
            ["PROD001", "electronics", 45, 500, 3, 1500, 30, 20, 15],
            ["PROD002", "furniture", 30, 300, 2, 12000, 100, 80, 50],
            ["PROD003", "toys", 25, 200, 5, 300, 15, 10, 8],
        ]
    },
    "olist_reviews": {
        "columns": ["review_id", "order_id", "review_score",
                     "review_comment_title", "review_comment_message",
                     "review_creation_date", "review_answer_timestamp"],
        "rows": [
            ["REV001", "ORD001", 5, "Great", "Very fast delivery", "2024-01-21 10:00:00", "2024-01-21 10:30:00"],
            ["REV002", "ORD003", 4, None, "Good product", "2024-01-23 14:00:00", "2024-01-23 14:15:00"],
            ["REV003", "ORD005", 3, "OK", None, "2024-01-26 09:00:00", "2024-01-26 09:20:00"],
        ]
    },
}


def download_dataset(name: str, data_dir: str) -> bool:
    csv_path = os.path.join(data_dir, f"{name}.csv")
    parquet_path = os.path.join(data_dir, f"{name}.parquet")

    if os.path.exists(parquet_path):
        print(f"  [skip] {name}.parquet already exists")
        return True

    url = GITHUB_MIRROR.get(name)
    if url:
        try:
            import httpx
            print(f"  [download] {name} from GitHub mirror...")
            resp = httpx.get(url, timeout=120.0, follow_redirects=True)
            if resp.status_code == 200:
                from io import StringIO
                df = pd.read_csv(StringIO(resp.text))
                from datetime import datetime
                df["_ingested_at"] = datetime.now()
                df["_source"] = name
                df["_batch_id"] = "batch_1"
                os.makedirs(data_dir, exist_ok=True)
                df.to_parquet(parquet_path, index=False)
                print(f"  [ok] {name}: {len(df)} rows → {parquet_path}")
                return True
        except Exception as e:
            print(f"  [warn] GitHub download failed: {e}")

    print(f"  [fallback] Using sample data for {name}")
    sample = SAMPLE_DATA[name]
    df = pd.DataFrame(sample["rows"], columns=sample["columns"])
    from datetime import datetime
    df["_ingested_at"] = datetime.now()
    df["_source"] = name
    df["_batch_id"] = "batch_1"
    os.makedirs(data_dir, exist_ok=True)
    df.to_parquet(parquet_path, index=False)
    print(f"  [ok] {name}: {len(df)} rows (sample) → {parquet_path}")
    return True


def main():
    project_root = Path(__file__).parent.parent
    data_dir = str(project_root / "data" / "raw")

    print("DataMind Data Initialization")
    print("=" * 40)

    for name in KAGGLE_DATASETS:
        download_dataset(name, data_dir)

    print("\nDone! Raw data ready in data/raw/")


if __name__ == "__main__":
    main()
