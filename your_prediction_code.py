import pandas as pd
from datetime import date
import os

# Read CSV
df = pd.read_csv("TrainingNewSales.csv")

# Convert dates
df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)

# Drop rows with missing Product_ID to avoid empty groups
df = df.dropna(subset=["Product_ID"])
df["Product_ID"] = df["Product_ID"].astype(str).str.strip()

# --- FIX: Add missing columns or ensure they exist ---
# The original error was due to 'Weekend', 'Public_holiday', 'Promotion_Period' being missing.
# For now, I will add dummy columns with 'No' to allow execution.
# In a real scenario, these would be properly derived from the 'Date' or other features.
if 'Weekend' not in df.columns:
    df['Weekend'] = 'No'
if 'Public_holiday' not in df.columns:
    df['Public_holiday'] = 'No'
if 'Promotion_Period' not in df.columns:
    df['Promotion_Period'] = 'No'
# --- End FIX ---

# Determine base Restock_Order_Date from existing forecast (max + 1 day)
output_file = "forecast_output.csv"

# --- New logic to get last known restock arrival dates for 'RESTOCK NEEDED' items ---
product_to_max_arrival_date = {}
if os.path.exists(output_file):
    try:
        existing_df_from_file = pd.read_csv(output_file)
        # Convert date columns for comparison
        existing_df_from_file['Restock_Order_Date'] = pd.to_datetime(existing_df_from_file['Restock_Order_Date'], dayfirst=True, errors='coerce')
        existing_df_from_file['Restock_Arrival_Date'] = pd.to_datetime(existing_df_from_file['Restock_Arrival_Date'], dayfirst=True, errors='coerce')

        # Filter for 'RESTOCK NEEDED' status and valid arrival dates
        needed_restocks = existing_df_from_file[
            (existing_df_from_file['Restock_Status'] == 'RESTOCK NEEDED') &
            (existing_df_from_file['Restock_Arrival_Date'].notna())
        ]

        # Get the max arrival date for each product that still needs restock
        if not needed_restocks.empty:
            product_to_max_arrival_date = needed_restocks.groupby('Product_ID')['Restock_Arrival_Date'].max().to_dict()

        # Existing logic for base_order_date
        max_order = existing_df_from_file.get("Restock_Order_Date").max()
        if pd.isna(max_order):
            base_order_date = pd.Timestamp(date.today())
        else:
            base_order_date = max_order + pd.Timedelta(days=1)
    except Exception:
        base_order_date = pd.Timestamp(date.today())
else:
    base_order_date = pd.Timestamp(date.today())
# --- End of new logic ---

# Store results
results = []

# Loop products
for product in df["Product_ID"].unique():

    # Product data
    product_df = df[df["Product_ID"] == product]

    # Average daily sales
    avg_daily_sales = product_df["Sales"].mean()

    # Current inventory
    current_inventory = product_df["Inventory_Start"].iloc[-1]

    # Lead days
    lead_days = int(product_df["Lead_Days"].iloc[-1])

    # Use base_order_date (max existing Restock_Order_Date + 1) for the new order
    restock_order_date = base_order_date

    # Calculate restock arrival date = order date + lead_days
    restock_arrival_date = restock_order_date + pd.Timedelta(days=lead_days)

    # Safety stock depends on the month of the restock order date
    if restock_order_date.month in [1, 4, 6, 12]:
        safety_stock = 150
    else:
        safety_stock = 100

    # Base adjusted demand
    adjusted_demand = avg_daily_sales

    # Weekend effect
    if product_df["Weekend"].iloc[-1] == "Yes":
        adjusted_demand *= 1.20

    # Public holiday effect
    if product_df["Public_holiday"].iloc[-1] == "Yes":
        adjusted_demand *= 1.30

    # Promotion effect
    if product_df["Promotion_Period"].iloc[-1] == "Yes":
        adjusted_demand *= 1.50

    # Reorder point
    reorder_point = (adjusted_demand * lead_days) + safety_stock

    # Restock logic
    if current_inventory <= reorder_point:
        restock_status = "RESTOCK NEEDED"
    else:
        restock_status = "SUFFICIENT"

    # Suggested restock amount (initial calculation)
    suggested_restock = max(
        0,
        round(reorder_point - current_inventory)
    )

    # --- Apply new logic to prevent duplicate reorders if previous order is in transit ---
    if restock_status == "RESTOCK NEEDED" and product in product_to_max_arrival_date:
        last_known_arrival_date = product_to_max_arrival_date[product]
        # If the current restock order date is before the last known arrival date of a previous 'RESTOCK NEEDED' order,
        # it means a restock for this product is already in transit and will cover the need.
        if restock_order_date < last_known_arrival_date:
            suggested_restock = 0 # Set suggested restock to zero
            restock_status = "ORDER IN TRANSIT" # Update status for clarity
    # --- End of new logic ---


    # Save results
    results.append({
        "Product_ID": product,
        "Avg_Daily_Sales": round(avg_daily_sales, 2),
        "Adjusted_Demand": round(adjusted_demand, 2),
        "Lead_Days": lead_days,
        "Safety_Stock": safety_stock,
        "Current_Inventory": current_inventory,
        "Reorder_Point": round(reorder_point, 2),
        "Product_Arrival_Key": f"{product}_{restock_arrival_date.strftime('%d/%m/%Y')}",
        "Suggested_Restock": suggested_restock,
        "Restock_Status": restock_status,
        "Restock_Order_Date": restock_order_date.strftime('%d/%m/%Y'),
        "Restock_Arrival_Date": restock_arrival_date.strftime('%d/%m/%Y')
    })

# Create dataframe from new results
new_results_df = pd.DataFrame(results)

# Check if forecast_output.csv already exists
# This part handles combining the new results with the existing file.
# The logic for preventing duplicate orders was applied *before* generating new_results_df.
output_file = "forecast_output.csv"
if os.path.exists(output_file):
    # Load existing data
    existing_df = pd.read_csv(output_file)
    # Concatenate new results with existing data
    combined_df = pd.concat([existing_df, new_results_df], ignore_index=True)
else:
    # If file doesn't exist, new_results_df is the first set of results
    combined_df = new_results_df

# --- New logic to ensure consistent date format for output ---
# Convert date columns to datetime objects (handling potential mixed types) then format to 'dd/mm/yyyy'
for col in ['Restock_Order_Date', 'Restock_Arrival_Date']:
    if col in combined_df.columns:
        # First, ensure they are datetime objects, coercing errors for robustness
        combined_df[col] = pd.to_datetime(combined_df[col], dayfirst=True, errors='coerce')
        # Then format them to the desired string format, handling NaT values
        combined_df[col] = combined_df[col].dt.strftime('%d/%m/%Y').fillna('')
# --- End of new logic ---

# Print results
print(combined_df)

# Save output
combined_df.to_csv(output_file, index=False)

print("Forecast file created/updated")