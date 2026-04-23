import streamlit as st
from supabase import create_client, Client
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import base64
import io
import html as _html
import pandas as pd
from datetime import date


# -----------------------
# Helpers 
# -----------------------
def autopct_dollars(values):
    total = sum(values)
    def inner(pct):
        val = pct * total / 100.0
        return f"${val:,.2f}"
    return inner

def autopct_format(values):
	def inner(pct):
		total = sum(values)
		monthly = pct * total / 100.0
		yearly = monthly * 12
		return f"{pct:.1f}%\n${monthly:,.0f}/mo\n${yearly:,.0f}/yr"
	return inner


def print_row(label, monthly, income=None):
	yearly = monthly * 12
	if income is not None:
		pct = 100 * monthly / income
		return f"{label:<35} {monthly:>12,.2f}   {yearly:>12,.2f}   {pct:>7.2f}%"
	return f"{label:<35} {monthly:>12,.2f}   {yearly:>12,.2f}"

def fintech_bar(label, actual, budget, breakdown=None):
    """
    Renders a fintech-style progress bar with color thresholds and overspend info.
    """
    # Guard
    actual = float(actual or 0.0)
    budget = float(budget or 0.0)

    ratio = (actual / budget) if budget > 0 else 0.0
    pct = ratio * 100.0
    fill = min(pct, 100.0)

    amount_over_budget = actual - budget

    # Color rules
    if budget <= 0:
        color = "#9CA3AF"  # gray
    elif pct < 80:
        color = "#16A34A"  # green
    elif pct < 100:
        color = "#F59E0B"  # amber
    else:
        color = "#DC2626"  # red

    # Text: remaining vs over
    if budget > 0:
        delta = budget - actual
        status = f"Remaining: ${delta:,.0f}" if delta >= 0 else f"Over by: ${abs(delta):,.0f}"
        pct_text = f"{pct:,.0f}%"
    else:
        status = "No budget set"
        pct_text = "—"

    st.markdown(
        f"""
        <div style="margin: 10px 0 6px 0;">
          <div style="display:flex; justify-content:space-between; align-items:baseline;">
            <div style="font-weight:700; font-size: 1.0rem;">{label}</div>
            <div style="font-size:0.9rem; color:#6B7280;">{pct_text}</div>
          </div>

          <div style="display:flex; justify-content:space-between; margin-top:2px;">
            <div style="font-size:0.95rem;">${actual:,.0f} / ${budget:,.0f}</div>
            <div style="font-size:0.95rem; color:{'#DC2626' if (budget>0 and actual>budget) else '#16A34A' if (budget>0 and actual<=budget) else '#6B7280'};">
              {status}
            </div>
          </div>

          <div style="height: 10px; background: #E5E7EB; border-radius: 999px; overflow:hidden; margin-top: 6px;">
            <div style="width:{fill:.1f}%; height:100%; background:{color}; border-radius: 999px;"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if breakdown:
        st.caption(breakdown)

    # Optional warning callout
    if actual > budget:
        if budget > 0:
            st.warning(f"{label} is over budget by ${actual - budget:,.2f}", icon="⚠️")
        st.warning(f"${actual-budget:,.0f} taken from guilt-free spending")

def fixed_costs(rent=0, utilities=0, insurance=0, trans_travel=0, debt=0, food=0, clothes=0, phone=0, subs=0):
	fixed = rent + utilities + insurance + trans_travel + debt + food + clothes + phone + subs
	total = fixed

	lines = []
	lines.append("\nFIXED COSTS")
	lines.append("-" * 80)
	lines.append(f"{'Category':<35} {'Monthly':>12}   {'Yearly':>12}   {'% Income':>8}")
	lines.append("-" * 80)

	lines.append(print_row("Rent", rent))
	lines.append(print_row("Utilities", utilities))
	lines.append(print_row("Insurance", insurance))
	lines.append(print_row("Transportation/Travel", trans_travel))
	lines.append(print_row("Debt", debt))
	lines.append(print_row("Food", food))
	lines.append(print_row("Clothes", clothes))
	lines.append(print_row("Phone", phone))
	lines.append(print_row("Subscriptions", subs))

	return total, "\n".join(lines)


def post_tax_investments(roth=0, stocks=0, other=0):
	invest = roth + stocks + other

	lines = []
	lines.append("\nPOST-TAX INVESTMENTS")
	lines.append("-" * 80)
	lines.append(f"{'Category':<35} {'Monthly':>12}   {'Yearly':>12}   {'% Income':>8}")
	lines.append("-" * 80)

	lines.append(print_row("Roth IRA", roth))
	lines.append(print_row("Stocks", stocks))
	lines.append(print_row("Other", other))

	return invest, "\n".join(lines)


def savings(emergency=0, vacations=0, gifts=0, other=0):
	save = emergency + vacations + gifts + other

	lines = []
	lines.append("\nSAVINGS")
	lines.append("-" * 80)
	lines.append(f"{'Category':<35} {'Monthly':>12}   {'Yearly':>12}   {' % Income':>8}")
	lines.append("-" * 80)

	lines.append(print_row("Emergency Fund", emergency))
	lines.append(print_row("Vacations", vacations))
	lines.append(print_row("Gifts", gifts))
	lines.append(print_row("Other", other))

	return save, "\n".join(lines)


def projection_series_with_savings(pv, monthly_invest, monthly_savings, years, annual_returns=(0.05, 0.07, 0.09)):
	n = int(years * 12)
	t_years = [m / 12 for m in range(n + 1)]

	contrib_invest = [monthly_invest * m for m in range(n + 1)]
	savings_series = [monthly_savings * m for m in range(n + 1)]

	fv_map = {}
	for r in annual_returns:
		r_m = (1 + r) ** (1 / 12) - 1
		series = []
		for m in range(n + 1):
			if m == 0:
				series.append(pv)
				continue

			if abs(r_m) < 1e-12:
				fv_invest = pv + monthly_invest * m
			else:
				fv_invest = pv * (1 + r_m) ** m + monthly_invest * (((1 + r_m) ** m - 1) / r_m)

			series.append(fv_invest + savings_series[m])

		fv_map[r] = series

	return t_years, contrib_invest, savings_series, fv_map


def make_pie_fig(income, fixed, post_tax, save, guilt_free, pretax_401k, pretax_hsa):
	overall_labels = ["Fixed Costs", "Post-Tax Investments", "Savings", "Guilt-Free Spending"]
	overall_values = [fixed, post_tax, save, guilt_free]

	pretax_total = pretax_401k + pretax_hsa
	pretax_labels = ["401K", "HSA"]
	pretax_values = [pretax_401k, pretax_hsa]

	fig, ax = plt.subplots(1, 2, figsize=(14, 7))

	ax[0].pie(
		overall_values,
		labels=overall_labels,
		autopct=autopct_format(overall_values),
		startangle=90,
		wedgeprops={"edgecolor": "black"},
	)
	ax[0].set_title(f"Monthly Budget Allocation\nTotal Income: ${income:,.0f}", fontsize=12, pad=20)
	ax[0].axis("equal")

	ax[1].pie(
		pretax_values,
		labels=pretax_labels,
		autopct=autopct_format(pretax_values),
		startangle=90,
		wedgeprops={"edgecolor": "black"},
	)
	ax[1].set_title(f"Pre-Tax Investment Breakdown\nTotal Pre-Tax: ${pretax_total:,.0f}", fontsize=12, pad=20)
	ax[1].axis("equal")

	plt.tight_layout(rect=[0, 0, 1, 0.93])
	return fig


def make_projection_fig(t_years, contrib_invest, savings_series, fv_map):
	fig2 = plt.figure(figsize=(12, 6))
	ax2 = fig2.add_subplot(1, 1, 1)

	# Total contributions line (invest + savings)
	total_contrib = [a + b for a, b in zip(contrib_invest, savings_series)]

	ax2.plot(t_years, total_contrib, label="Total Contributions (Invest+Savings)")
	ax2.plot(t_years, fv_map[0.05], label="Net Worth @ 5%")
	ax2.plot(t_years, fv_map[0.07], label="Net Worth @ 7%")
	ax2.plot(t_years, fv_map[0.09], label="Net Worth @ 9%")

	ax2.fill_between(t_years, fv_map[0.05], fv_map[0.09], alpha=0.15)

	ax2.set_title("Contributions vs Net Worth Projection (5%, 7%, 9%)")
	ax2.set_xlabel("Years")
	ax2.set_ylabel("Dollars")
	ax2.grid(True, alpha=0.3)

	ax2.ticklabel_format(style="plain", axis="y")
	ax2.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))

	# Label lines near the right
	def label_line(ax, x, y, text, x_pos=0.92):
		x_min, x_max = ax.get_xlim()
		x_target = x_min + x_pos * (x_max - x_min)
		idx = min(range(len(x)), key=lambda i: abs(x[i] - x_target))
		ax.text(x[idx], y[idx], f"  {text}", va="center")

	label_line(ax2, t_years, total_contrib, "Total Contributions")
	label_line(ax2, t_years, fv_map[0.05], "Net Worth @ 5%")
	label_line(ax2, t_years, fv_map[0.07], "Net Worth @ 7%")
	label_line(ax2, t_years, fv_map[0.09], "Net Worth @ 9%")

	return fig2


def make_budget_text(income, fixed_block, post_block, savings_block, fixed, post_tax, save, guilt_free, pretax_401k, pretax_hsa):
	lines = []
	lines.append("\nBUDGET SUMMARY")
	lines.append("=" * 80)
	lines.append(f"{'Category':<35} {'Monthly':>12}   {'Yearly':>12}   {'% Income':>8}")
	lines.append("-" * 80)

	lines.append(print_row("Net Income", income))
	lines.append(print_row("Total Income", income + pretax_401k + pretax_hsa))
	lines.append("-" * 80)

	lines.append(fixed_block)
	lines.append(print_row("Total Fixed Costs", fixed, income))
	lines.append("-" * 80)

	lines.append(post_block)
	lines.append(print_row("Total Post-Tax Investments", post_tax, income))
	lines.append("-" * 80)

	lines.append("\nPRE-TAX INVESTMENTS")
	lines.append("-" * 80)
	lines.append(f"{'Category':<35} {'Monthly':>12}   {'Yearly':>12}   {'% Income':>8}")
	lines.append("-" * 80)
	lines.append(print_row("401K", pretax_401k))
	lines.append(print_row("HSA", pretax_hsa))
	lines.append(print_row("Total Pre-Tax Investment", pretax_401k + pretax_hsa))
	lines.append("-" * 80)

	lines.append(savings_block)
	lines.append(print_row("Total Savings", save, income))
	lines.append("-" * 80)

	lines.append(print_row("Total Guilt-Free Spending", guilt_free, income))
	lines.append("=" * 80)
	lines.append(f"Weekly Guilt-Free Spending = {guilt_free / 4:.2f}$")

	return "\n".join(lines)


def money(x): 
    return f"${float(x):,.0f}"

def pct(x): 
    return f"{100*float(x):.0f}%"

def progress_bar(value, max_value):
    value = float(value or 0.0)
    max_value = float(max_value or 0.0)
    ratio = (value / max_value) if max_value > 0 else 0.0
    ratio_clamped = min(max(ratio, 0.0), 1.0)
    # color thresholds
    if max_value <= 0:
        color = "#9CA3AF"
    elif ratio < 0.8:
        color = "#16A34A"
    elif ratio < 1.0:
        color = "#F59E0B"
    else:
        color = "#DC2626"
    return f"""
      <div class="bar">
        <div class="barfill" style="width:{ratio_clamped*100:.1f}%; background:{color};"></div>
      </div>
    """

def make_budget_html(
    timestamp,
    income,
    pretax_401k,
    pretax_hsa,
    fixed,
    post_tax,
    save,
    guilt_free,
    fixed_block_text="",
    post_block_text="",
    savings_block_text="",
    pie_b64=None,
    proj_b64=None,
):
    fixed_pct = fixed / income if income else 0.0
    post_pct  = post_tax / income if income else 0.0
    save_pct  = save / income if income else 0.0
    guilt_pct = guilt_free / income if income else 0.0

    total_income = income + pretax_401k + pretax_hsa
    weekly_guilt = guilt_free / 4.0

    def card(label, value, sub=""):
        return f"""
        <div class="card">
          <div class="label">{_html.escape(label)}</div>
          <div class="value">{_html.escape(value)}</div>
          <div class="sub">{_html.escape(sub)}</div>
        </div>
        """

    # Use <pre> blocks as a safe fallback until you add structured line items
    fixed_pre   = _html.escape(fixed_block_text or "").strip()
    post_pre    = _html.escape(post_block_text or "").strip()
    savings_pre = _html.escape(savings_block_text or "").strip()

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />

  <style>
    :root {{
      --bg: #F5F7FB;
      --card: #FFFFFF;
      --text: #111827;
      --muted: #6B7280;
      --border: #E5E7EB;
    }}
    body {{
      margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: var(--bg); color: var(--text);
    }}
    .wrap {{ max-width: 1050px; margin: 28px auto; padding: 0 18px; }}
    h1 {{ margin: 0 0 6px; font-size: 28px; }}
    .meta {{ color: var(--muted); margin-bottom: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
    .card {{
      background: var(--card); border: 1px solid var(--border); border-radius: 14px;
      padding: 14px 14px 12px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }}
    .label {{ color: var(--muted); font-size: 12px; letter-spacing: 0.02em; text-transform: uppercase; }}
    .value {{ font-size: 22px; font-weight: 700; margin-top: 6px; }}
    .sub {{ color: var(--muted); font-size: 12px; margin-top: 6px; }}
    .section {{ margin-top: 16px; }}
    .panel {{
      background: var(--card); border: 1px solid var(--border); border-radius: 14px;
      padding: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }}
    .row {{
      display:flex; justify-content:space-between; align-items:baseline; gap: 10px;
      margin: 10px 0 8px;
    }}
    .row .name {{ font-weight: 700; }}
    .row .nums {{ color: var(--muted); font-size: 14px; white-space: nowrap; }}
    .bar {{ height: 10px; background: #E5E7EB; border-radius: 999px; overflow: hidden; }}
    .barfill {{ height: 100%; border-radius: 999px; }}
    .twocol {{ display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    img {{ max-width: 100%; border-radius: 12px; border: 1px solid var(--border); background: #fff; }}
    pre {{
      background: #0B1020; color: #E5E7EB; padding: 12px; border-radius: 12px;
      overflow-x: auto; font-size: 12px; line-height: 1.4;
    }}
    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: repeat(2, 1fr); }}
      .twocol {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>

<body>
  <div class="wrap">
    <div class="meta">Generated: {_html.escape(timestamp)}</div>

    <div class="grid">
      {card("Net Income (Monthly)", money(income), "After taxes")}
      {card("Total Income (Monthly)", money(total_income), "Including 401k + HSA")}
      {card("Guilt-Free (Monthly)", money(guilt_free), f"Weekly: {money(weekly_guilt)}")}
      {card("Fixed Costs (Monthly)", money(fixed), f"Share of income: {pct(fixed_pct)}")}
    </div>

    <div class="section panel">
      <div class="row">
        <div class="name">Fixed Costs</div>
        <div class="nums">{money(fixed)} • {pct(fixed_pct)}</div>
      </div>
      {progress_bar(fixed, income)}
      <div style="margin-top:10px;">
        <pre>{fixed_pre}</pre>
      </div>
    </div>

    <div class="section panel">
      <div class="row">
        <div class="name">Post-Tax Investments</div>
        <div class="nums">{money(post_tax)} • {pct(post_pct)}</div>
      </div>
      {progress_bar(post_tax, income)}
      <div style="margin-top:10px;">
        <pre>{post_pre}</pre>
      </div>
    </div>

    <div class="section panel">
      <div class="row">
        <div class="name">Savings</div>
        <div class="nums">{money(save)} • {pct(save_pct)}</div>
      </div>
      {progress_bar(save, income)}
      <div style="margin-top:10px;">
        <pre>{savings_pre}</pre>
      </div>
    </div>

    <div class="section panel">
      <div class="row">
        <div class="name">Guilt-Free Spending</div>
        <div class="nums">{money(guilt_free)} • {pct(guilt_pct)} • Weekly {money(weekly_guilt)}</div>
      </div>
      {progress_bar(guilt_free, income)}
    </div>

 

  </div>
</body>
</html>
"""

def fig_to_png_bytes(fig):
	buf = io.BytesIO()
	fig.savefig(buf, format="png", bbox_inches="tight")
	buf.seek(0)
	return buf.read()


def fig_to_base64_png(fig):
	return base64.b64encode(fig_to_png_bytes(fig)).decode("utf-8")


# -----------------------
# Supabase UI
# -----------------------
#@st.cache_resource
def init_connection():
	url = st.secrets["SUPABASE_URL"]
	key = st.secrets["SUPABASE_KEY"]
	if "supabase_client" not in st.session_state:
		st.session_state["supabase_client"] = create_client(url,key)
	return st.session_state["supabase_client"]


def set_session(session):
    st.session_state["sb_access_token"] = session.access_token
    st.session_state["sb_refresh_token"] = session.refresh_token

def clear_session():
    st.session_state.clear()

def restore_session(supabase):
	at = st.session_state.get("sb_access_token")
	rt = st.session_state.get("sb_refresh_token")
	if at and rt:
	    # refreshes if needed
	    supabase.auth.set_session(at, rt)
	    return True
	return False

def load_profile_data(supabase, user_id: str) -> dict:
    restore_session(supabase)
    res = (
        supabase.table("budget_profile")
        .select("data")
        .eq("id", user_id)
        .single()
        .execute()
    )
    # data is JSONB in DB -> comes back as a Python dict or None
    return res.data.get("data") if res.data and res.data.get("data") else {}

def save_profile_data(supabase, user_id: str, data: dict):
    restore_session(supabase)
    return (
        supabase.table("budget_profile")
        .update({"data": data})
        .eq("id", user_id)
        .execute()
    )

# --- Cache the Supabase client (resource cache) ---
@st.cache_resource
def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def init_connection():
    # keep your app.py call sites unchanged
    return get_supabase_client()


# --- Cached READS (data cache) ---
@st.cache_data(ttl=60)
def fetch_budget_profile(user_id: str) -> dict:
    sb = get_supabase_client()
    restore_session(sb)
    res = (
        sb.table("budget_profile")
        .select("data, display_name")
        .eq("id", user_id)
        .single()
        .execute()
    )
    return res.data or {}

@st.cache_data(ttl=30)
def fetch_expenses_month(user_id: str, start_iso: str, end_iso: str) -> pd.DataFrame:
    sb = get_supabase_client()
    restore_session(sb)
    res = (
        sb.table("expense_profile")
        .select("expense_date, category, amount")
        .eq("id", user_id)
        .gte("expense_date", start_iso)
        .lte("expense_date", end_iso)
        .execute()
    )
    rows = res.data or []
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["expense_date", "category", "amount"])
    if not df.empty:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    return df

@st.cache_data(ttl=30)
def fetch_expenses_range(user_id: str, start_iso: str, end_iso: str) -> list:
    sb = get_supabase_client()
    restore_session(sb)
    res = (
        sb.table("expense_profile")
        .select("id, expense_id, expense_date, category, amount, created_at, Notes")
        .eq("id", user_id)
        .gte("expense_date", start_iso)
        .lte("expense_date", end_iso)
        .order("expense_date", desc=True)
        .execute()
    )
    return res.data or []

@st.cache_data(ttl=120)
def fetch_monthly_expense_totals() -> pd.DataFrame:
    sb = get_supabase_client()
    restore_session(sb)
    monthly = sb.rpc("monthly_expense_totals", {"start_date": None, "end_date": None}).execute()
    dfm = pd.DataFrame(monthly.data)
    if not dfm.empty:
        dfm["month"] = pd.to_datetime(dfm["month"])
        dfm["total"] = dfm["total"].astype(float)
    return dfm


# --- Cache invalidation helpers (call after writes) ---
def clear_profile_cache():
    fetch_budget_profile.clear()

def clear_expense_cache():
    fetch_expenses_month.clear()
    fetch_expenses_range.clear()
    fetch_monthly_expense_totals.clear()
