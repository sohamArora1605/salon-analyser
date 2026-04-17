from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetSpec:
    file_name: str
    domain: str
    target_table: str
    description: str


DATASETS: tuple[DatasetSpec, ...] = (
    DatasetSpec(
        file_name="Future Bookings (All Clients)0.csv",
        domain="appointments",
        target_table="appointments",
        description="Forward-looking appointment bookings with client code, staff, service, date, and time.",
    ),
    DatasetSpec(
        file_name="Client Cancellations0.csv",
        domain="cancellations",
        target_table="cancellations",
        description="Client cancellation events tied back to booking dates.",
    ),
    DatasetSpec(
        file_name="No-Show Report0.csv",
        domain="no_shows",
        target_table="no_shows",
        description="No-show appointments by date, client code, service, and staff.",
    ),
    DatasetSpec(
        file_name="salon_noshow_data.csv",
        domain="synthetic_no_show_features",
        target_table="cancellations",
        description="Richer generated cancellation/no-show-style features for later ML experiments.",
    ),
    DatasetSpec(
        file_name="Product Listing (Retail)0.csv",
        domain="products",
        target_table="products",
        description="Retail product catalog, stock levels, costs, and year-to-date values.",
    ),
    DatasetSpec(
        file_name="Service Listing0.csv",
        domain="services",
        target_table="services",
        description="Service catalog with category, price, and cost.",
    ),
    DatasetSpec(
        file_name="Receipt Transactions0.csv",
        domain="receipts",
        target_table="receipt_transactions",
        description="Sales/service receipt line items by date, client, staff, quantity, taxes, and amount.",
    ),
    DatasetSpec(
        file_name="hair_salon_no_show_wrangled_df.csv",
        domain="ml_seed",
        target_table="ml_seed_events",
        description="Wrangled historical no-show data retained as a flexible ML seed dataset.",
    ),
)

