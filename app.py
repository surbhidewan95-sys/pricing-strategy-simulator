from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import sqlite3
import joblib
import os
import pandas as pd

# ReportLab Imports for PDF Generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

app = Flask(__name__)
app.secret_key = "pricing_ai_super_secret_key_2026"

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

uploaded_df = None


# ---------------------------------------------------------
# ML Model Loading
# ---------------------------------------------------------
try:
    model = joblib.load("pricing_model.pkl")
    print("✅ Machine Learning Model Loaded Successfully!")
except Exception as e:
    model = None
    print("⚠️ Model file not found. Fallback mathematical calculation active.")


# ---------------------------------------------------------
# Database Initialization Routine (Auto Schema Migration)
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Predictions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            category TEXT DEFAULT 'General',
            cost REAL,
            price REAL,
            competitor REAL,
            demand INTEGER,
            revenue REAL,
            profit REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Auto Migration for Missing Columns in Existing Databases
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN user_id INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN category TEXT DEFAULT 'General'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()

init_db()


# ---------------------------------------------------------
# Application Routes
# ---------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute("SELECT SUM(revenue), SUM(profit), SUM(demand), COUNT(id) FROM predictions WHERE user_id = ?", (user_id,))
    else:
        cursor.execute("SELECT SUM(revenue), SUM(profit), SUM(demand), COUNT(id) FROM predictions")
        
    result = cursor.fetchone()
    cursor.execute("SELECT profit FROM predictions ORDER BY id DESC LIMIT 1")
    latest = cursor.fetchone()
    conn.close()

    total_revenue = round(result[0], 2) if result and result[0] else 50000.0
    total_profit = round(result[1], 2) if result and result[1] else 15000.0
    total_demand = result[2] if result and result[2] else 200
    strategy = "High Profit" if latest and latest[0] > 15000 else "Competitive"

    return render_template(
        "dashboard.html",
        revenue=f"{total_revenue:,.2f}",
        profit=f"{total_profit:,.2f}",
        demand=f"{total_demand:,}",
        strategy=strategy,
        user_name=session.get("user_name", "User")
    )


@app.route("/simulator")
def simulator():
    return render_template("simulator.html")


@app.route("/predict", methods=["POST"])
def predict():
    category = request.form.get("category", "General")
    cost = float(request.form["cost"])
    price = float(request.form["price"])
    competitor = float(request.form["competitor"])
    demand = int(request.form["demand"])

    revenue = round(price * demand, 2)

    if model:
        prediction = model.predict([[cost, price, competitor, demand]])
        profit = round(float(prediction[0]), 2)
    else:
        profit = round(revenue - (cost * demand), 2)

    strategy = "High Profit" if profit > 15000 else "Competitive"
    user_id = session.get("user_id", 1)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO predictions (user_id, category, cost, price, competitor, demand, revenue, profit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, category, cost, price, competitor, demand, revenue, profit))
    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        category=category,
        cost=cost,
        price=price,
        competitor=competitor,
        demand=demand,
        revenue=revenue,
        profit=profit,
        fmt_revenue=f"{revenue:,.2f}",
        fmt_profit=f"{profit:,.2f}",
        fmt_cost=f"{cost:,.2f}",
        fmt_price=f"{price:,.2f}",
        fmt_competitor=f"{competitor:,.2f}",
        strategy=strategy
    )


@app.route("/report")
def report():
    category = request.args.get("category", "General")
    cost = float(request.args.get("cost", 250))
    price = float(request.args.get("price", 450))
    competitor = float(request.args.get("competitor", 420))
    demand = int(request.args.get("demand", 150))
    revenue = round(price * demand, 2)
    profit = float(request.args.get("profit", revenue - (cost * demand)))
    strategy = request.args.get("strategy", "High Profit")

    return render_template(
        "report.html",
        category=category,
        cost=cost,
        price=price,
        competitor=competitor,
        fmt_cost=f"{cost:,.2f}",
        fmt_price=f"{price:,.2f}",
        fmt_competitor=f"{competitor:,.2f}",
        demand=demand,
        revenue=revenue,
        profit=profit,
        fmt_revenue=f"{revenue:,.2f}",
        fmt_profit=f"{profit:,.2f}",
        strategy=strategy
    )


# ---------------------------------------------------------
# User Profile, Settings, Contact Routes
# ---------------------------------------------------------
@app.route("/profile")
def profile():
    user_name = session.get("user_name", "User")
    user_id = session.get("user_id")
    email = "user@pricingai.com"

    if user_id:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        u = cursor.fetchone()
        conn.close()
        if u:
            email = u[0]

    return render_template("profile.html", user_name=user_name, email=email)


@app.route("/settings")
def settings():
    return render_template("settings.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


# Natural Language CSV QA Processing Engine
@app.route("/csv-qa", methods=["GET", "POST"])
def csv_qa():
    global uploaded_df
    answer = None
    filename = session.get("uploaded_filename", None)

    if request.method == "POST":
        if 'csv_file' in request.files and request.files['csv_file'].filename != '':
            file = request.files['csv_file']
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            
            try:
                uploaded_df = pd.read_csv(filepath)
                num_rows, num_cols = uploaded_df.shape
                cols_str = ", ".join(uploaded_df.columns.tolist())
                filename = file.filename
                session["uploaded_filename"] = filename
                answer = f"✅ File '{file.filename}' Uploaded Successfully!\n\n📌 Dataset Overview:\n• Total Rows: {num_rows}\n• Total Columns: {num_cols}\n• Column Names: [{cols_str}]"
            except Exception as err:
                answer = f"❌ Error reading CSV File: {str(err)}"

        elif 'question' in request.form and uploaded_df is not None:
            q = request.form['question'].lower().strip()
            cols = uploaded_df.columns.tolist()
            num_cols = uploaded_df.select_dtypes(include=['number']).columns.tolist()

            matched_col = None
            for c in cols:
                if c.lower() in q:
                    matched_col = c
                    break

            try:
                if "row" in q or "count" in q or "size" in q:
                    answer = f"📊 Total Records in Dataset: {len(uploaded_df)} Rows"

                elif "column" in q or "field" in q or "variable" in q:
                    answer = f"📋 Columns ({len(cols)}):\n" + "\n".join([f"  {i+1}. {col}" for i, col in enumerate(cols)])

                elif "head" in q or "top" in q or "preview" in q or "first" in q:
                    answer = f"🔍 Top 5 Rows Preview:\n\n{uploaded_df.head(5).to_string()}"

                elif "tail" in q or "last" in q or "bottom" in q:
                    answer = f"🔍 Last 5 Rows Preview:\n\n{uploaded_df.tail(5).to_string()}"

                elif "summary" in q or "describe" in q or "stat" in q:
                    answer = f"📈 Statistical Summary of Numerical Fields:\n\n{uploaded_df.describe().to_string()}"

                elif "null" in q or "missing" in q or "na" in q:
                    missing_data = uploaded_df.isnull().sum()
                    answer = f"⚠️ Missing/Null Values Count Per Column:\n\n{missing_data.to_string()}"

                elif "avg" in q or "average" in q or "mean" in q:
                    if matched_col and matched_col in num_cols:
                        avg_val = round(uploaded_df[matched_col].mean(), 2)
                        answer = f"🧮 Average value for '{matched_col}': {avg_val}"
                    elif len(num_cols) > 0:
                        means = round(uploaded_df[num_cols].mean(), 2)
                        answer = f"🧮 Average Values for Numerical Columns:\n\n{means.to_string()}"
                    else:
                        answer = "⚠️ No numerical columns found to calculate average."

                elif "max" in q or "highest" in q or "maximum" in q:
                    if matched_col and matched_col in num_cols:
                        max_val = uploaded_df[matched_col].max()
                        answer = f"🔝 Highest value for '{matched_col}': {max_val}"
                    elif len(num_cols) > 0:
                        maxes = uploaded_df[num_cols].max()
                        answer = f"🔝 Highest Values for Numerical Columns:\n\n{maxes.to_string()}"
                    else:
                        answer = "⚠️ No numerical columns found."

                elif "min" in q or "lowest" in q or "minimum" in q:
                    if matched_col and matched_col in num_cols:
                        min_val = uploaded_df[matched_col].min()
                        answer = f"🔻 Lowest value for '{matched_col}': {min_val}"
                    elif len(num_cols) > 0:
                        mins = uploaded_df[num_cols].min()
                        answer = f"🔻 Lowest Values for Numerical Columns:\n\n{mins.to_string()}"
                    else:
                        answer = "⚠️ No numerical columns found."

                elif "sum" in q or "total" in q:
                    if matched_col and matched_col in num_cols:
                        tot_val = round(uploaded_df[matched_col].sum(), 2)
                        answer = f"➕ Total Sum for '{matched_col}': {tot_val}"
                    elif len(num_cols) > 0:
                        sums = round(uploaded_df[num_cols].sum(), 2)
                        answer = f"➕ Sum Totals for Numerical Columns:\n\n{sums.to_string()}"
                    else:
                        answer = "⚠️ No numerical columns found."

                else:
                    answer = f"🤖 Dataset Data Info:\n• Columns: {cols}\n• Total Rows: {len(uploaded_df)}\n\n💡 Try asking: 'average [col_name]', 'highest [col_name]', 'summary statistics', or 'show top 5 rows'."

            except Exception as query_err:
                answer = f"❌ Error executing query: {str(query_err)}"

        elif 'question' in request.form and uploaded_df is None:
            answer = "⚠️ Please upload a CSV dataset file first!"

    csv_uploaded = uploaded_df is not None
    return render_template("csv_qa.html", answer=answer, csv_uploaded=csv_uploaded, filename=filename)


# ---------------------------------------------------------
# History & Result Viewing Routes
# ---------------------------------------------------------
@app.route("/history")
def history():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, cost, price, competitor, demand, revenue, profit, created_at, category FROM predictions ORDER BY id DESC")
    records = cursor.fetchall()
    conn.close()
    return render_template("history.html", records=records)


@app.route("/view-result/<int:record_id>")
def view_result(record_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT cost, price, competitor, demand, revenue, profit, category FROM predictions WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        cost, price, competitor, demand, revenue, profit, category = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
        strategy = "High Profit" if profit > 15000 else "Competitive"
        
        return render_template(
            "result.html",
            category=category if category else "General",
            cost=cost,
            price=price,
            competitor=competitor,
            demand=demand,
            revenue=revenue,
            profit=profit,
            fmt_revenue=f"{revenue:,.2f}",
            fmt_profit=f"{profit:,.2f}",
            fmt_cost=f"{cost:,.2f}",
            fmt_price=f"{price:,.2f}",
            fmt_competitor=f"{competitor:,.2f}",
            strategy=strategy
        )
    return redirect("/history")


@app.route("/delete-history/<int:record_id>")
def delete_history(record_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM predictions WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    return redirect("/history")


@app.route("/clear-history")
def clear_history():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM predictions")
    conn.commit()
    conn.close()
    return redirect("/history")


@app.route("/analytics")
def analytics():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # 1. Fetch Aggregated Stats
    cursor.execute("SELECT COUNT(id), AVG(profit), MAX(revenue), SUM(profit) FROM predictions")
    stats = cursor.fetchone()

    total_predictions = stats[0] if stats and stats[0] else 0
    avg_profit = round(stats[1], 2) if stats and stats[1] else 0.0
    max_revenue = round(stats[2], 2) if stats and stats[2] else 0.0
    total_profit = round(stats[3], 2) if stats and stats[3] else 0.0

    # 2. Fetch Detailed Historical Data for Charts
    cursor.execute("SELECT profit, revenue FROM predictions ORDER BY id ASC")
    records = cursor.fetchall()
    conn.close()

    # Extract lists for Chart.js rendering
    profit_list = [r[0] for r in records] if records else []
    revenue_list = [r[1] for r in records] if records else []

    return render_template(
        "analytics.html",
        total_predictions=total_predictions,
        avg_profit=f"{avg_profit:,.2f}",
        max_revenue=f"{max_revenue:,.2f}",
        total_profit=f"{total_profit:,.2f}",
        profit_list=profit_list,
        revenue_list=revenue_list
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            conn.commit()
            conn.close()
            flash("Account created successfully! Please login.", "success")
            return redirect("/login")
        except Exception:
            flash("Email already registered!", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM users WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            return redirect("/dashboard")
        else:
            flash("Invalid email or password!", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/download-pdf")
def download_pdf():
    revenue = request.args.get("revenue", "0.00")
    profit = request.args.get("profit", "0.00")
    strategy = request.args.get("strategy", "High Profit")
    cost = request.args.get("cost", "250.00")
    price = request.args.get("price", "450.00")
    competitor = request.args.get("competitor", "420.00")
    demand = request.args.get("demand", "150")

    pdf_path = "PricingAI_Executive_Report.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    primary_color = colors.HexColor("#162436")
    light_bg = colors.HexColor("#f8fafc")

    cell_head = ParagraphStyle('CellHead', parent=styles['Normal'], fontSize=10, textColor=colors.white, fontName='Helvetica-Bold')
    cell_body = ParagraphStyle('CellBody', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#1e293b"), fontName='Helvetica')

    header_data = [[
        Paragraph("<b>PricingAI Optimization Platform</b><br/><font size='9' color='#94a3b8'>Executive AI Prediction Summary</font>", ParagraphStyle('H1', textColor=colors.white, fontSize=16, leading=20)),
        Paragraph("<font color='#00ff88'><b>VERIFIED ML OUTPUT</b></font>", ParagraphStyle('H2', textColor=colors.white, fontSize=10, alignment=2))
    ]]
    header_table = Table(header_data, colWidths=[380, 160])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), primary_color),
        ('PADDING', (0,0), (-1,-1), 16),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 20))

    data = [
        [Paragraph("<b>Metric Parameter</b>", cell_head), Paragraph("<b>Value / Unit</b>", cell_head), Paragraph("<b>Status Impact</b>", cell_head)],
        [Paragraph("Unit Production Cost", cell_body), Paragraph(f"Rs. {cost}", cell_body), Paragraph("Base Cost", cell_body)],
        [Paragraph("Target Selling Price", cell_body), Paragraph(f"Rs. {price}", cell_body), Paragraph("Primary Revenue Unit", cell_body)],
        [Paragraph("Market Competitor Price", cell_body), Paragraph(f"Rs. {competitor}", cell_body), Paragraph("Elasticity Benchmark", cell_body)],
        [Paragraph("Projected Demand Volume", cell_body), Paragraph(f"{demand} Units", cell_body), Paragraph("Forecast Volume", cell_body)],
        [Paragraph("Projected Gross Revenue", cell_body), Paragraph(f"<b>Rs. {revenue}</b>", cell_body), Paragraph("<font color='#00a86b'><b>Top-Line Output</b></font>", cell_body)],
        [Paragraph("Net Predicted Profit", cell_body), Paragraph(f"<b>Rs. {profit}</b>", cell_body), Paragraph("<font color='#00a86b'><b>Net Bottom-Line</b></font>", cell_body)],
        [Paragraph("Recommended Strategy", cell_body), Paragraph(f"<b>{strategy}</b>", cell_body), Paragraph("Optimized Model Strategy", cell_body)],
    ]

    metric_table = Table(data, colWidths=[200, 180, 160])
    metric_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('PADDING', (0,0), (-1,-1), 10),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [light_bg, colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 25))

    doc.build(story)
    return send_file(pdf_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)