import pandas as pd
from datetime import date
import os

def run_forecast(df: pd.DataFrame, existing_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Core forecast logic. Accepts dataframes instead of reading from disk.
    Returns a DataFrame of results.
    """

    # Convert dates

    df["Date"] = pd.to_datetime(df["Date"])

# =========================
# CREATE MONTHLY SUMMARY
# =========================

df["Year"] = df["Date"].dt.year
df["Month"] = df["Date"].dt.month

monthly_summary = (
    df.groupby(["Year", "Month", "Product_ID"])
    .agg({
        "Sales": "sum",
        "Inventory_Start": "last",
        "Lead_Days": "last"
    })
    .reset_index()
)

# Rename grouped sales
monthly_summary = monthly_summary.rename(
    columns={"Sales": "Monthly_Sales"}
)

# Average monthly sales per product
avg_sales_per_product = (
    monthly_summary.groupby("Product_ID")["Monthly_Sales"]
    .mean()
    .reset_index()
)

avg_sales_per_product = avg_sales_per_product.rename(
    columns={"Monthly_Sales": "Avg_Monthly_Sales"}
)

    # Drop rows with missing Product_ID
    df = df.dropna(subset=["Product_ID"])
    df["Product_ID"] = df["Product_ID"].astype(str).str.strip()

    # Add missing columns if not present
    if 'Weekend' not in df.columns:
        df['Weekend'] = 'No'
    if 'Public_holiday' not in df.columns:
        df['Public_holiday'] = 'No'
    if 'Promotion_Period' not in df.columns:
        df['Promotion_Period'] = 'No'

    # Determine base_order_date and product_to_max_arrival_date
    product_to_max_arrival_date = {}
    base_order_date = pd.Timestamp(date.today())

    if existing_df is not None and not existing_df.empty:
        try:
            existing_df['Restock_Order_Date'] = pd.to_datetime(
                existing_df['Restock_Order_Date'], dayfirst=True, errors='coerce'
            )
            existing_df['Restock_Arrival_Date'] = pd.to_datetime(
                existing_df['Restock_Arrival_Date'], dayfirst=True, errors='coerce'
            )

            needed_restocks = existing_df[
                (existing_df['Restock_Status'] == 'RESTOCK NEEDED') &
                (existing_df['Restock_Arrival_Date'].notna())
            ]

            if not needed_restocks.empty:
                product_to_max_arrival_date = (
                    needed_restocks.groupby('Product_ID')['Restock_Arrival_Date']
                    .max().to_dict()
                )

            max_order = existing_df["Restock_Order_Date"].max()
            if not pd.isna(max_order):
                base_order_date = max_order + pd.Timedelta(days=1)

        except Exception:
            base_order_date = pd.Timestamp(date.today())

    # Loop products and build results
    results = []

for product in monthly_summary["Product_ID"].unique():

    product_df = monthly_summary[
        monthly_summary["Product_ID"] == product
    ]

    avg_monthly_sales = (
        avg_sales_per_product[
            avg_sales_per_product["Product_ID"] == product
        ]["Avg_Monthly_Sales"].iloc[0]
    )


        current_inventory = product_df["Inventory_Start"].iloc[-1]
        lead_days = int(product_df["Lead_Days"].iloc[-1])

        restock_order_date = base_order_date
        restock_arrival_date = restock_order_date + pd.Timedelta(days=lead_days)

        safety_stock = 150 if restock_order_date.month in [1, 4, 6, 12] else 100

        adjusted_demand = avg_monthly_sales

        if product_df["Weekend"].iloc[-1] == "Yes":
            adjusted_demand *= 1.20
        if product_df["Public_holiday"].iloc[-1] == "Yes":
            adjusted_demand *= 1.30
        if product_df["Promotion_Period"].iloc[-1] == "Yes":
            adjusted_demand *= 1.50

        reorder_point = (adjusted_demand * lead_days) + safety_stock
        restock_status = "RESTOCK NEEDED" if current_inventory <= reorder_point else "SUFFICIENT"
        suggested_restock = max(0, round(reorder_point - current_inventory))

        if restock_status == "RESTOCK NEEDED" and product in product_to_max_arrival_date:
            if restock_order_date < product_to_max_arrival_date[product]:
                suggested_restock = 0
                restock_status = "ORDER IN TRANSIT"

        results.append({
            "Product_ID": product,
            "Avg_Monthly_Sales": round(avg_monthly_sales, 2),
            "Adjusted_Demand": round(adjusted_demand, 2),
            "Lead_Days": lead_days,
            "Safety_Stock": safety_stock,
            "Current_Inventory": current_inventory,
            "Reorder_Point": round(reorder_point, 2),
            "Product_Arrival_Key": f"{product}_{restock_arrival_date.strftime('%Y%m%d')}"
            "Suggested_Restock": suggested_restock,
            "Restock_Status": restock_status,
            "Restock_Order_Date": restock_order_date.strftime('%d/%m/%Y'),
            "Restock_Arrival_Date": restock_arrival_date.strftime('%d/%m/%Y')
        })

    return pd.DataFrame(results)


def predict_sales(data: dict) -> list:
    """
    Flask endpoint function.
    Accepts: { "records": [ {Product_ID, Date, Sales, Inventory_Start, Lead_Days, ...} ] }
    Returns: list of forecast dicts
    """
    records = data.get("records", [])
    if not records:
        raise ValueError("No records provided in payload")

    df = pd.DataFrame(records)

    # Rename SharePoint columns

    df = df.rename(columns={

        "Title": "Product_ID",
        "field_1": "Date",
        "field_3": "Lead_Days",
        "field_4": "Sales",
        "field_6": "Inventory_Start"

    })
    # Load existing forecast if it exists (optional — remove if deploying stateless)
    existing_df = None
    if os.path.exists("forecast_output.csv"):
        existing_df = pd.read_csv("forecast_output.csv")

    result_df = run_forecast(df, existing_df)

    # Convert to plain Python types for JSON serialisation
    return result_df.to_dict(orient="records")


def calculate_restock(data: dict) -> list:
    """
    Same logic — alias endpoint focused on restock output only.
    Filters to only RESTOCK NEEDED / ORDER IN TRANSIT rows.
    """
    all_results = predict_sales(data)
    restock_only = [
        r for r in all_results
        if r["Restock_Status"] in ("RESTOCK NEEDED", "ORDER IN TRANSIT")
    ]
    return restock_only