import streamlit as st
from supabase import create_client, Client
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import base64
import io


# -----------------------
# Helpers (same as your script)
# -----------------------
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


def fixed_costs(rent=0, utilities=0, insurance=0, trans_travel=0, debt=0, food=0, clothes=0, phone=0, subs=0):
	fixed = rent + utilities + insurance + trans_travel + debt + food + clothes + phone + subs
	misc = 0.15 * fixed
	total = fixed + misc

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
	lines.append(print_row("Misc (15%)", misc))

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
    st.session_state["access_token"] = session.access_token
    st.session_state["refresh_token"] = session.refresh_token

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
