from datetime import datetime

import streamlit as st
from supabase import create_client, Client
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

# If you still want to use your existing function:
from income_calc import income_c
from helpers import *


# Connect to supabase
supabase = init_connection()
restore_session(supabase)

u = supabase.auth.get_user()
user_id = u.user.id if (u and u.user) else None

saved_data = None
if user_id:
    res_data = (
        supabase.table("budget_profile")
        .select("data")
        .eq("id", user_id)
        .single()
        .execute()
    )
    saved_data = res_data.data.get("data") if res_data.data else None


st.set_page_config(page_title="Budget Dashboard", layout="wide")
# -----------------------
# Streamlit UI
# -----------------------
tab1,tab2,tab3 = st.tabs(["Login/Register", "Dashboard", "Expense Tracker"])

with tab1:
	#with st.sidebar:
	st.header("Account")

	mode = st.radio("Mode", ["Login", "Register"], horizontal=True)

	email = st.text_input("Email")
	password = st.text_input("Password", type="password")

	if mode == "Register":
		if st.button("Create account", use_container_width=True):
			#try:
			res = supabase.auth.sign_up({"email": email, "password": password})
			st.success("Account created.")# Check your email if confirmations are enabled.")
			# If email confirmation is OFF, Supabase may return a session immediately:
			if res.session:
				set_session(res.session)
				st.rerun()

	if mode == "Login":
		if st.button("Login", use_container_width=True):
		    
			email_norm = email.strip().lower()

			res = supabase.auth.sign_in_with_password({"email": email_norm,"password": password})
			if 'user' in res:
				set_session(res.session)
				st.success("Sucess!")
				st.rerun()


	# Show current user + logout
	restore_session(supabase)
	u = supabase.auth.get_user()
	if u and u.user:

		user_id = u.user.id
		res = (
		    supabase.table("budget_profile")
		    .select("display_name")
		    .eq("id", user_id)
		    .single()
		    .execute()
		)
		display_name = res.data.get("display_name") if res.data else None

		st.divider()
		st.write(f"Signed in as: **{u.user.email}**")
		st.write("Current display name:", display_name)

		if st.button("Logout", use_container_width=True):
		    clear_session()
		    st.rerun()

		with st.form("display_name_form"):
		    new_name = st.text_input("New Display Name", value=display_name or "")
		    submitted = st.form_submit_button("Change display name")

		if submitted:
		    restore_session(supabase)  # safe to call again
		    out = (
		        supabase.table("budget_profile")
		        .update({"display_name": new_name})
		        .eq("id", user_id)
		        .execute()
		    )

		    st.success("New display name saved.")
		    st.rerun()

with tab2:
	st.title("Monthly Budget Dashboard")

	if not user_id:
		st.info("Log in to load saved settings")
	else:
		with st.sidebar:
			if saved_data is not None:
			    if st.button("Load Saved Profile Settings",use_container_width=True):
			        for key, value in saved_data.items():
			            st.session_state[key] = value
			        st.sidebar.success("Saved settings loaded.")
			        st.rerun()

			if st.button("Save profile settings", use_container_width=True):
				profile_payload = {
				"annual_salary": st.session_state["annual_salary"],
				"pretax_401k_annual": st.session_state["pretax_401k_annual"],
				"match_rate": st.session_state["match_rate"],
				"hsa_monthly_in": st.session_state["hsa_monthly_in"],
				"healthcare_monthly_premium": st.session_state["healthcare_monthly_premium"],
				"other_income": st.session_state["other_income"],

				"rent_in": st.session_state["rent_in"],
				"utilities_in": st.session_state["utilities_in"],
				"insurance_in": st.session_state["insurance_in"],
				"trans_travel_in": st.session_state["trans_travel_in"],
				"food_in": st.session_state["food_in"],
				"debt_in": st.session_state["debt_in"],
				"clothes_in": st.session_state["clothes_in"],
				"phone_in": st.session_state["phone_in"],
				"subs_in": st.session_state["subs_in"],

				"roth_in": st.session_state["roth_in"],
				"stocks_in": st.session_state["stocks_in"],
				"post_other_in": st.session_state["post_other_in"],

				"emergency_in": st.session_state["emergency_in"],
				"vacations_in": st.session_state["vacations_in"],
				"gifts_in": st.session_state["gifts_in"],
				"save_other_in": st.session_state["save_other_in"],

				"current_cash": st.session_state["current_cash"],
				"current_investments": st.session_state["current_investments"],
				}
				out = save_profile_data(supabase, user_id, profile_payload)
				st.sidebar.success("Saved your profile!")
			    # optional: st.write(out.data)
	DEFAULTS = {
	    "annual_salary": 50000.0,
	    "pretax_401k_annual": 10.0,
	    "match_rate": 0.0,
	    "hsa_monthly_in": 0.0,
	    "healthcare_monthly_premium": 0.0,
	    "other_income": 0.0,
	    "rent_in": 1000.0,
	    "utilities_in": 100.0,
	    "insurance_in": 0.0,
	    "trans_travel_in": 100.0,
	    "food_in": 100.0,
	    "debt_in": 0.0,
	    "clothes_in": 100.0,
	    "phone_in": 0.0,
	    "subs_in": 0.0,
	    "roth_in": 0.0,
	    "stocks_in": 0.0,
	    "post_other_in": 0.0,
	    "emergency_in": 0.0,
	    "vacations_in": 0.0,
	    "gifts_in": 0.0,
	    "save_other_in": 0.0,
	    "current_cash": 0.0,
	    "current_investments": 0.0,
	}

	for k, v in DEFAULTS.items():
	    st.session_state.setdefault(k, v)

	with st.sidebar:
		st.header("Income")
		annual_salary = st.number_input("Pretax Annual salary", min_value=0.0, step=1000.0, key="annual_salary")
		pretax_401k_annual = st.number_input("401k annual contribution", min_value=0.0, step=500.0,key="pretax_401k_annual")
		match_rate = st.number_input("Employer match rate (decimal)", min_value=0.0, max_value=1.0, step=0.01,key="match_rate")
		hsa_monthly_in = st.number_input("HSA monthly contribution", min_value=0.0,key="hsa_monthly_in")
		healthcare_monthly_premium = st.number_input("Healthcare monthly premium", min_value=0.0, step=50.0,key="healthcare_monthly_premium")
		other_income = st.number_input("Other monthly income (Spouse aftertax)",min_value=0.0,step=100.0,key="other_income")

		st.divider()
		st.header("Fixed Costs (monthly)")
		rent_in = st.number_input("Rent", min_value=0.0, step=50.0,key="rent_in")
		utilities_in = st.number_input("Utilities", min_value=0.0, step=25.0,key="utilities_in")
		insurance_in = st.number_input("Insurance", min_value=0.0, step=25.0,key="insurance_in")
		trans_travel_in = st.number_input("Transportation/Travel", min_value=0.0, step=25.0,key="trans_travel_in")
		food_in = st.number_input("Food/Groceries", min_value=0.0, step=25.0,key="food_in")
		debt_in = st.number_input("Debt", min_value=0.0, step=10.0,key="debt_in")
		clothes_in = st.number_input("Clothes", min_value=0.0, step=25.0,key="clothes_in")
		phone_in = st.number_input("Phone", min_value=0.0, step=10.0,key="phone_in")
		subs_in = st.number_input("Subscriptions", min_value=0.0, step=25.0,key="subs_in")

		st.divider()
		st.header("Post-tax Investments (monthly)")
		roth_in = st.number_input("Roth (monthly)", min_value=0.0, step=50.0,key="roth_in")
		stocks_in = st.number_input("Stocks (monthly)", min_value=0.0, step=50.0,key="stocks_in")
		post_other_in = st.number_input("Other post-tax (monthly)", min_value=0.0, step=25.0,key="post_other_in")

		st.divider()
		st.header("Savings (monthly, 0% return)")
		emergency_in = st.number_input("Emergency fund", min_value=0.0, step=50.0,key="emergency_in")
		vacations_in = st.number_input("Vacations", min_value=0.0, step=50.0,key="vacations_in")
		gifts_in = st.number_input("Gifts", min_value=0.0, step=25.0,key="gifts_in")
		save_other_in = st.number_input("Other savings", min_value=0.0, step=25.0,key="save_other_in")

		st.divider()
		st.header("Net Worth")
		current_cash = st.number_input("Current cash", min_value=0.0, step=1000.0,key="current_cash")
		current_investments = st.number_input("Current investments", min_value=0.0, step=5000.0,key="current_investments")

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

with tab3:
	st.title("Expenses")
	st.write("put expenses here")

# Cleanup matplotlib objects
plt.close(pie_fig)
plt.close(proj_fig)