import streamlit as st
import pandas as pd
import altair as alt
import requests

# Configure the page
st.set_page_config(
    page_title="Compare Life Expectancy by Country",
    layout="wide"
)

# World Bank public API:
# SP.DYN.LE00.IN = Life expectancy at birth, total (years)
WORLD_BANK_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/"
    "SP.DYN.LE00.IN?format=json&per_page=20000"
)

@st.cache_data(ttl=86400)
def load_data():
    """Load life-expectancy data from the World Bank public API."""

    response = requests.get(WORLD_BANK_URL, timeout=30)
    response.raise_for_status()

    api_response = response.json()

    # World Bank responses use:
    # item 0 = page metadata
    # item 1 = observation rows
    if not isinstance(api_response, list) or len(api_response) < 2:
        raise ValueError("Unexpected response received from the World Bank API.")

    records = api_response[1]

    rows = []

    for record in records:
        life_expectancy = record.get("value")
        country = record.get("country", {}).get("value")
        country_code = record.get("countryiso3code")
        year = record.get("date")

        if (
            life_expectancy is not None
            and country
            and country_code
            and year
        ):
            rows.append({
                "Country": country,
                "Country Code": country_code,
                "Year": int(year),
                "Life Expectancy": float(life_expectancy)
            })

    data = pd.DataFrame(rows)

    if data.empty:
        raise ValueError("The World Bank API returned no usable data.")

    # Exclude regional and income-group aggregates.
    # World Bank country codes are generally three letters.
    data = data[data["Country Code"].str.len() == 3].copy()

    return data


# Load public data
try:
    data = load_data()
except Exception as error:
    st.error("The public life-expectancy data could not be loaded.")
    st.exception(error)
    st.stop()

# App title and instructions
st.title("Compare Life Expectancy by Country")
st.write(
    "Select two countries and a year range to compare life expectancy trends "
    "and the difference between them."
)

# Available selections
countries = sorted(data["Country"].unique().tolist())
min_year = int(data["Year"].min())
max_year = int(data["Year"].max())

# Country-selection controls
country_column_1, country_column_2 = st.columns(2)

with country_column_1:
    country_1 = st.selectbox(
        "Country 1",
        countries,
        index=countries.index("United States")
        if "United States" in countries
        else 0
    )

with country_column_2:
    default_country_2 = "Canada" if "Canada" in countries else countries[1]

    country_2 = st.selectbox(
        "Country 2",
        countries,
        index=countries.index(default_country_2)
    )

# Year-range selection
default_start_year = max(min_year, 2000)
default_end_year = min(max_year, 2023)

start_year, end_year = st.slider(
    "Year range",
    min_value=min_year,
    max_value=max_year,
    value=(default_start_year, default_end_year)
)

# Prevent an invalid comparison
if country_1 == country_2:
    st.warning("Please select two different countries.")
    st.stop()

# Filter data to selected countries and years
selected_data = data[
    (data["Country"].isin([country_1, country_2]))
    & (data["Year"].between(start_year, end_year))
].copy()

# Build a side-by-side comparison table
comparison = selected_data.pivot(
    index="Year",
    columns="Country",
    values="Life Expectancy"
).reset_index()

# Retain both selected country columns even if one has no data
for country in [country_1, country_2]:
    if country not in comparison.columns:
        comparison[country] = pd.NA

comparison = comparison[["Year", country_1, country_2]]

difference_column = f"{country_1} minus {country_2}"
comparison[difference_column] = comparison[country_1] - comparison[country_2]

comparison = comparison.sort_values("Year")

# Display comparison table
st.subheader("Comparison Results")

formatted_comparison = comparison.style.format({
    country_1: "{:.2f}",
    country_2: "{:.2f}",
    difference_column: "{:.2f}"
})

st.dataframe(
    formatted_comparison,
    use_container_width=True,
    hide_index=True
)

# Get the latest year containing values for both countries
complete_results = comparison.dropna(
    subset=[country_1, country_2, difference_column]
)

if complete_results.empty:
    st.info(
        "No complete comparison data is available for the selected countries "
        "and year range."
    )
else:
    latest = complete_results.iloc[-1]

    latest_year = int(latest["Year"])
    country_1_value = float(latest[country_1])
    country_2_value = float(latest[country_2])
    difference = float(latest[difference_column])

    # Latest-year metrics
    metric_1, metric_2, metric_3 = st.columns(3)

    metric_1.metric(
        f"{country_1} ({latest_year})",
        f"{country_1_value:.2f} years"
    )

    metric_2.metric(
        f"{country_2} ({latest_year})",
        f"{country_2_value:.2f} years"
    )

    metric_3.metric(
        "Difference",
        f"{difference:.2f} years"
    )

    # Clear result statement
    if difference > 0:
        st.success(
            f"✅ **{country_1}** has the longer life expectancy in "
            f"**{latest_year}** — by **{difference:.2f} years**."
        )
    elif difference < 0:
        st.success(
            f"✅ **{country_2}** has the longer life expectancy in "
            f"**{latest_year}** — by **{abs(difference):.2f} years**."
        )
    else:
        st.info(
            f"ℹ️ **{country_1}** and **{country_2}** have the same life "
            f"expectancy in **{latest_year}**."
        )

    # Latest-year visual comparison
    latest_comparison = pd.DataFrame({
        "Country": [country_1, country_2],
        "Life Expectancy": [country_1_value, country_2_value]
    })

    latest_bar_chart = alt.Chart(latest_comparison).mark_bar().encode(
        x=alt.X(
            "Life Expectancy:Q",
            title="Life expectancy (years)",
            scale=alt.Scale(zero=False)
        ),
        y=alt.Y(
            "Country:N",
            sort="-x",
            title=None
        ),
        color=alt.Color(
            "Country:N",
            legend=None
        ),
        tooltip=[
            alt.Tooltip("Country:N", title="Country"),
            alt.Tooltip(
                "Life Expectancy:Q",
                title="Life expectancy",
                format=".2f"
            )
        ]
    ).properties(
        title=f"Which Country Has Higher Life Expectancy? ({latest_year})",
        height=180
    )

    st.altair_chart(latest_bar_chart, use_container_width=True)

# Prepare data for the trend chart
chart_data = comparison.melt(
    id_vars="Year",
    value_vars=[country_1, country_2],
    var_name="Country",
    value_name="Life Expectancy"
).dropna()

# Trend chart
trend_chart = alt.Chart(chart_data).mark_line(point=True).encode(
    x=alt.X("Year:O", title="Year"),
    y=alt.Y(
        "Life Expectancy:Q",
        title="Life expectancy (years)"
    ),
    color=alt.Color(
        "Country:N",
        title="Country"
    ),
    tooltip=[
        alt.Tooltip("Year:O", title="Year"),
        alt.Tooltip("Country:N", title="Country"),
        alt.Tooltip(
            "Life Expectancy:Q",
            title="Life expectancy",
            format=".2f"
        )
    ]
).properties(
    height=400
)

st.subheader("Life Expectancy Trend")
st.altair_chart(trend_chart, use_container_width=True)

st.caption(
    "Data source: World Bank, Life expectancy at birth, total (years), "
    "indicator SP.DYN.LE00.IN. This app is for educational and "
    "demonstration purposes."
)
