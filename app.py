from flask import Flask, render_template, request, send_file
import pandas as pd
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

output_path = None


def find_column(columns, keywords):
    """
    Find first column containing any keyword.
    """
    for col in columns:
        col_lower = str(col).strip().lower()

        for keyword in keywords:
            if keyword in col_lower:
                return col

    return None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():
    global output_path

    try:
        master = request.files["master_file"]
        report = request.files["report_file"]

        master_path = os.path.join(
            UPLOAD_FOLDER,
            master.filename
        )

        report_path = os.path.join(
            UPLOAD_FOLDER,
            report.filename
        )

        master.save(master_path)
        report.save(report_path)

        # Read Master File
        if master.filename.lower().endswith(".csv"):
            master_df = pd.read_csv(master_path)
        else:
            master_df = pd.read_excel(master_path)

        # Read Report File
        if report.filename.lower().endswith(".csv"):
            report_df = pd.read_csv(report_path)
        else:
            report_df = pd.read_excel(report_path)

        # Clean column names
        master_df.columns = master_df.columns.astype(str).str.strip()
        report_df.columns = report_df.columns.astype(str).str.strip()

        print("MASTER COLUMNS:", master_df.columns.tolist())
        print("REPORT COLUMNS:", report_df.columns.tolist())

        # Detect ASIN column in master
        master_asin = find_column(
            master_df.columns,
            ["asin"]
        )

        # Detect SKU column in master
        master_sku = find_column(
            master_df.columns,
            ["sku"]
        )

        if master_asin is None:
            return (
                f"ASIN column not found in Master File.<br>"
                f"Columns Found: {master_df.columns.tolist()}"
            )

        if master_sku is None:
            return (
                f"SKU column not found in Master File.<br>"
                f"Columns Found: {master_df.columns.tolist()}"
            )

        # Detect ASIN column in report
        report_asin = find_column(
            report_df.columns,
            ["asin"]
        )

        if report_asin is None:
            return (
                f"ASIN column not found in Report File.<br>"
                f"Columns Found: {report_df.columns.tolist()}"
            )

        # Rename columns
        master_df = master_df.rename(
            columns={
                master_asin: "ASIN",
                master_sku: "SKU"
            }
        )

        report_df = report_df.rename(
            columns={
                report_asin: "ASIN"
            }
        )

        # Convert to string
        master_df["ASIN"] = (
            master_df["ASIN"]
            .astype(str)
            .str.strip()
        )

        report_df["ASIN"] = (
            report_df["ASIN"]
            .astype(str)
            .str.strip()
        )

        # Merge report with master
        merged = report_df.merge(
            master_df[["ASIN", "SKU"]],
            on="ASIN",
            how="left"
        )

        total_rows = len(merged)
        matched = merged["SKU"].notna().sum()
        missing = merged["SKU"].isna().sum()

        output_path = os.path.join(
            OUTPUT_FOLDER,
            "processed_report.xlsx"
        )

        merged.to_excel(
            output_path,
            index=False
        )

        stats = {
            "total_rows": int(total_rows),
            "matched": int(matched),
            "missing": int(missing)
        }

        return render_template(
            "index.html",
            stats=stats
        )

    except Exception as e:
        return f"Error: {str(e)}"


@app.route("/download")
def download():
    global output_path

    if output_path and os.path.exists(output_path):
        return send_file(
            output_path,
            as_attachment=True
        )

    return "No processed file available."

@app.route("/")
def reset():
    global output_path

    output_path = None

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)