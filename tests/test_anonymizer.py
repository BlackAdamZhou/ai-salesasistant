import pandas as pd

from app.anonymizer import anonymise_product_names


def test_anonymise_product_names_uses_stable_codes():
    df = pd.DataFrame({"product_name": ["Banana", "Apple", "Banana"]})

    anonymised, mapping = anonymise_product_names(df)

    assert mapping == {"Apple": "Product_001", "Banana": "Product_002"}
    assert anonymised["product_code"].tolist() == [
        "Product_002",
        "Product_001",
        "Product_002",
    ]

