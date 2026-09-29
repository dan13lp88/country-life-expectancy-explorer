import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(
    page_title="Compare Life Expectancy by Country",
    layout="wide"
)

DATA_URL = (
    "https://ourworldindata.org/grapher/life-expectancy-hmd-unwpp.csv"
)

@st.cache_data
def load_data():
    data = pd.read_csv(DATA_URL)

    # The published indicator can be named differently over time.
    # Identify the non-metadata numeric column that represents life expectancy.
    metadata_columns = ["Entity", "Code", "Year"]
    value_columns = [
        column for column in data.columns
        if column not in metadata_columns
    ]

    if not value_columns:
        raise ValueError(
            "Could not find a life expectancy value column in the public dataset."
        )

    life_expectancy_column = value_columns[0]

    data = data.rename(columns={
        "Entity": "Country",
        "Year": "Year",
        life_expectancy_column: "Life Expectancy"
    })

    data = data[[
        "Country",
        "Year",
        "Life Expectancy"
    ]].dropna()

    return data


try:
    data = load_data()
except Exception as error:
    st.error("The public life-expectancy data could not be loaded.")
    st.exception(error)
    st.stop()

st.title("Compare Life Expectancy by Country")
st.write(
    "Select two countries and a year range to compare life expectancy trends "
    "and the difference between them."
)

countries = sorted(data["Country"].unique().tolist())
min_year = int(data["Year"].min())
max_year = int(data["Year"].max())

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

default_start_year = max(min_year, 2000)
default_end_year = min(max_year, 2023)

start_year, end_year = st.slider(
    "Year range",
    min_value=min_year,
    max_value=max_year,
    value=(default_start_year, default_end_year)
)

if country_1 == country_2:
    st.warning("Please select two different countries.")
    st.stop()

selected_data = data[
    (data["Country"].isin([country_1, country_2]))
    & (data["Year"].between(start_year, end_year))
].copy()

comparison = selected_data.pivot(
    index="Year",
    columns="Country",
    values="Life Expectancy"
).reset_index()

# Ensure country columns remain in the same order as the user selections.
for country in [country_1, country_2]:
    if country not in comparison.columns:
        comparison[country] = pd.NA

comparison = comparison[["Year", country_1, country_2]]
difference_column = f"{country_1} minus {country_2}"
comparison[difference_column] = comparison[country_1] - comparison[country_2]

st.subheader("Comparison results")
st.dataframe(
    comparison,
    use_container_width=True,
    hide_index=True
)

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

chart_data = comparison.melt(
    id_vars="Year",
    value_vars=[country_1, country_2],
    var_name="Country",
    value_name="Life Expectancy"
).dropna()

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
).properties(height=400)

st.subheader("Life Expectancy Trend")
st.altair_chart(trend_chart, use_container_width=True)

st.caption(
    "Data source: Our World in Data. This app is for educational and "
    "demonstration purposes."
)
