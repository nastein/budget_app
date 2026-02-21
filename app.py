import io
import base64
from datetime import datetime

import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

# If you still want to use your existing function:
from income_calc import income_c


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
# Streamlit UI
# -----------------------
st.set_page_config(page_title="Budget Dashboard", layout="wide")

st.title("Monthly Budget Dashboard")

with st.sidebar:
	st.header("Income")
	annual_salary = st.number_input("Pretax Annual salary", min_value=0.0, value=50000., step=1000.0)
	pretax_401k_annual = st.number_input("401k annual contribution", min_value=0.0, value=10., step=500.0)
	match_rate = st.number_input("Employer match rate (decimal)", min_value=0.0, max_value=1.0, value=0., step=0.01)
	hsa_monthly_in = st.number_input("HSA monthly contribution", min_value=0.0, value=0., step=50.0)
	healthcare_monthly_premium = st.number_input("Healthcare monthly premium", min_value=0.0, value=0., step=50.0)
	other_income = st.number_input("Other monthly income (Spouse aftertax)",min_value=0.0,value=0.,step=100.0)

	st.divider()
	st.header("Fixed Costs (monthly)")
	rent_in = st.number_input("Rent", min_value=0.0, value=1000., step=50.0)
	utilities_in = st.number_input("Utilities", min_value=0.0, value=100.0, step=25.0)
	insurance_in = st.number_input("Insurance", min_value=0.0, value=0.0, step=25.0)
	trans_travel_in = st.number_input("Transportation/Travel", min_value=0.0, value=100., step=25.0)
	food_in = st.number_input("Food/Groceries", min_value=0.0, value=100., step=25.0)
	debt_in = st.number_input("Debt", min_value=0.0, value=0., step=10.0)
	clothes_in = st.number_input("Clothes", min_value=0.0, value=100., step=25.0)
	phone_in = st.number_input("Phone", min_value=0.0, value=0.0, step=10.0)
	subs_in = st.number_input("Subscriptions", min_value=0.0, value=0., step=25.0)

	st.divider()
	st.header("Post-tax Investments (monthly)")
	roth_in = st.number_input("Roth (monthly)", min_value=0.0, value=0., step=50.0)
	stocks_in = st.number_input("Stocks (monthly)", min_value=0.0, value=0., step=50.0)
	post_other_in = st.number_input("Other post-tax (monthly)", min_value=0.0, value=0.0, step=25.0)

	st.divider()
	st.header("Savings (monthly, 0% return)")
	emergency_in = st.number_input("Emergency fund", min_value=0.0, value=0., step=50.0)
	vacations_in = st.number_input("Vacations", min_value=0.0, value=0.0, step=50.0)
	gifts_in = st.number_input("Gifts", min_value=0.0, value=0.0, step=25.0)
	save_other_in = st.number_input("Other savings", min_value=0.0, value=0.0, step=25.0)

	st.divider()
	st.header("Net Worth")
	current_cash = st.number_input("Current cash", min_value=0.0, value=0., step=1000.0)
	current_investments = st.number_input("Current investments", min_value=0.0, value=0., step=5000.0)

	st.divider()
	st.header("Projection")
	projection_years = st.slider("Years", min_value=1, max_value=60, value=25, step=1)

# Compute Noah income + pre-tax items
noahs_income, pretax_401k_monthly, hsa_monthly = income_c(
	annual_salary,
	pretax_401k_annual,
	match_rate,
	hsa_monthly_in,
	healthcare_monthly_premium
)

income = float(other_income + noahs_income)

# Budget pieces
fixed, fixed_block = fixed_costs(
	rent=rent_in,
	utilities=utilities_in,
	insurance=insurance_in,
	trans_travel=trans_travel_in,
	debt=debt_in,
	food=food_in,
	clothes=clothes_in,
	phone=phone_in,
	subs=subs_in
)

post_tax, post_block = post_tax_investments(roth=roth_in, stocks=stocks_in, other=post_other_in)
save, savings_block = savings(emergency=emergency_in, vacations=vacations_in, gifts=gifts_in, other=save_other_in)

guilt_free = income - fixed - post_tax - save

# Net worth
current_net_worth = float(current_cash + current_investments)

# Projection (invest earns return, savings earns 0%)
monthly_invest = float(pretax_401k_monthly + hsa_monthly + post_tax)
monthly_savings = float(save)
annual_contrib_total = (monthly_invest + monthly_savings) * 12

returns = (0.05, 0.07, 0.09)
t_years, contrib_invest, savings_series, fv_map = projection_series_with_savings(
	pv=current_net_worth,
	monthly_invest=monthly_invest,
	monthly_savings=monthly_savings,
	years=projection_years,
	annual_returns=returns
)

# Charts
pie_fig = make_pie_fig(income, fixed, post_tax, save, guilt_free, pretax_401k_monthly, hsa_monthly)
proj_fig = make_projection_fig(t_years, contrib_invest, savings_series, fv_map)

# Text report
budget_text = make_budget_text(
	income=income,
	fixed_block=fixed_block,
	post_block=post_block,
	savings_block=savings_block,
	fixed=fixed,
	post_tax=post_tax,
	save=save,
	guilt_free=guilt_free,
	pretax_401k=pretax_401k_monthly,
	pretax_hsa=hsa_monthly
)

timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")

# Layout
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
col1.metric("Current Net Worth", f"${current_net_worth:,.0f}")
col2.metric("Monthly Added (Invest + Savings)", f"${(monthly_invest + monthly_savings):,.0f}/mo")
col3.metric("Annual Added (Invest + Savings)", f"${annual_contrib_total:,.0f}/yr")
col4.metric("Weekly Guild Free Spending", f"${guilt_free / 4:,.2f}/wk")



st.subheader("Budget Report")
st.code(budget_text)

st.subheader("Charts")
st.pyplot(pie_fig, clear_figure=True)
st.pyplot(proj_fig, clear_figure=True)

# Download buttons
st.download_button(
	"Download budget report (.txt)",
	data=budget_text.encode("utf-8"),
	file_name="budget_output.txt",
	mime="text/plain"
)

# Optional: download the HTML dashboard too
pie_b64 = fig_to_base64_png(pie_fig)
proj_b64 = fig_to_base64_png(proj_fig)

html = f"""<!doctype html>
<html>
<head>
	<meta charset="utf-8" />
	<title>Budget Dashboard</title>
</head>
<body>
	<h1>Monthly Budget Dashboard</h1>
	<p>Generated: {timestamp}</p>

	<h2>Charts</h2>
	<img style="max-width:1100px;width:100%;" src="data:image/png;base64,{pie_b64}" />
	<img style="max-width:1100px;width:100%; margin-top:16px;" src="data:image/png;base64,{proj_b64}" />

	<h2>Budget Report</h2>
	<pre>{budget_text}</pre>
</body>
</html>
"""

st.download_button(
	"Download dashboard (.html)",
	data=html.encode("utf-8"),
	file_name="budget_dashboard.html",
	mime="text/html"
)

# Cleanup matplotlib objects
plt.close(pie_fig)
plt.close(proj_fig)