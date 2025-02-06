import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import pandas as pd
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

# -------------------------------
# 1) Load Your Data
# -------------------------------
df_maven = pd.read_csv("maven_orders.csv", parse_dates=["Date"])
df_market = pd.read_csv("coffee_market.csv", parse_dates=["Date"])

# Remove time zones if present and sort by date ascending
df_maven["Date"] = df_maven["Date"].dt.tz_localize(None)
df_market["Date"] = df_market["Date"].dt.tz_localize(None)
df_maven.sort_values("Date", inplace=True)
df_market.sort_values("Date", inplace=True)

# Create a "candlestick-ready" DataFrame for the Market.
# We'll make each row's "Open" be the previous row's "Close".
# "Close" is the current date's MarketPrices.
df_market_candle = df_market.copy()
df_market_candle["Open"] = df_market_candle["MarketPrices"].shift(1)
df_market_candle["Close"] = df_market_candle["MarketPrices"]
df_market_candle["High"] = df_market_candle[["Open", "Close"]].max(axis=1)
df_market_candle["Low"]  = df_market_candle[["Open", "Close"]].min(axis=1)
df_market_candle.dropna(subset=["Open"], inplace=True)

# Unique Products
unique_products = sorted(df_maven["Product"].dropna().unique())

# Default date range from Maven data
default_start = df_maven["Date"].min().date()
default_end = df_maven["Date"].max().date()

# -------------------------------
# Helper Function: KPI Card Style
# -------------------------------
def _card_style():
    return {
        "border": "1px solid #444",
        "padding": "10px",
        "width": "180px",
        "textAlign": "center",
        "borderRadius": "5px",
        "backgroundColor": "#333",
        "color": "white"
    }

# -------------------------------
# 2) Dash App Layout (with Dark Theme)
# -------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server
app.title = "Maven vs. Market Candlestick"

app.layout = html.Div([
    html.H1("Maven vs. Coffee Market (Candlestick)", style={"textAlign": "center", "color": "white"}),

    html.Div([
        html.P("Data source for market prices: Yahoo Finance (Coffee KC=F).", style={"color": "white"}),
        html.P("Candlestick: Up if today's price is higher than yesterday's close, down otherwise.", style={"color": "white"})
    ], style={"textAlign": "center"}),

    # Dropdown and Date Picker with Reset Button
    html.Div([
        html.Label("Select a Product:", style={"color": "white"}),
        dcc.Dropdown(
            id="product-dropdown",
            options=[{"label": p, "value": p} for p in unique_products],
            value=unique_products[0],
            clearable=False,
            style={"width": "300px", "color": "black"}
        ),
        html.Br(),
        html.Label("Select Date Range:", style={"color": "white"}),
        dcc.DatePickerRange(
            id="date-picker",
            min_date_allowed=df_maven["Date"].min().date(),
            max_date_allowed=df_maven["Date"].max().date(),
            start_date=default_start,
            end_date=default_end,
            display_format='YYYY-MM-DD'
        ),
        html.Br(),
        html.Button("Reset Date Range", id="reset-date-btn", n_clicks=0, style={"marginTop": "10px"})
    ], style={"textAlign": "center", "margin": "20px"}),

    # KPI area
    html.Div(
        id="kpi-container",
        style={
            "display": "flex",
            "justifyContent": "center",
            "gap": "20px",
            "marginBottom": "20px"
        }
    ),

    # Main chart: Combined candlestick (market) + Maven pricing line & bars
    dcc.Graph(id="price-graph")
], style={"backgroundColor": "#222", "padding": "20px"})

# -------------------------------
# 3) Callback to Reset Date Picker
# -------------------------------
@app.callback(
    [Output("date-picker", "start_date"),
     Output("date-picker", "end_date")],
    [Input("reset-date-btn", "n_clicks")]
)
def reset_date_range(n_clicks):
    if n_clicks:
        # Reset to default date range as string in ISO format.
        return str(default_start), str(default_end)
    return dash.no_update, dash.no_update

# -------------------------------
# 4) Callback to Update Dashboard
# -------------------------------
@app.callback(
    [Output("price-graph", "figure"),
     Output("kpi-container", "children")],
    [Input("product-dropdown", "value"),
     Input("date-picker", "start_date"),
     Input("date-picker", "end_date")]
)
def update_dashboard(selected_product, start_date, end_date):
    # ---------------------
    # (A) Filter Maven data by product and date range
    # ---------------------
    dff_maven = df_maven[(df_maven["Product"] == selected_product) &
                         (df_maven["Date"] >= pd.to_datetime(start_date)) &
                         (df_maven["Date"] <= pd.to_datetime(end_date))].copy()
    if dff_maven.empty:
        blank_fig = go.Figure()
        return blank_fig, [html.Div("No data for this product in the selected date range.", style={"color": "red"})]

    # ---------------------
    # (B) Build the figure
    # ---------------------
    fig = go.Figure()

    # 1) Market as Candlesticks from df_market_candle filtered by date range
    dff_market_candle = df_market_candle[(df_market_candle["Date"] >= pd.to_datetime(start_date)) &
                                         (df_market_candle["Date"] <= pd.to_datetime(end_date))]
    fig.add_trace(go.Candlestick(
        x=dff_market_candle["Date"],
        open=dff_market_candle["Open"],
        high=dff_market_candle["High"],
        low=dff_market_candle["Low"],
        close=dff_market_candle["Close"],
        name="Market Price (KC=F)",
        increasing_line_color="green",
        decreasing_line_color="red",
        showlegend=True
    ))

    # 2) Maven Bag Price as line+markers
    fig.add_trace(go.Scatter(
        x=dff_maven["Date"],
        y=dff_maven["BagPrice"],
        mode="lines+markers",
        name="Maven Bag Price",
        line=dict(color="blue", width=2),
        marker=dict(size=5, color="blue")
    ))

    # 3) Bars for Bags on secondary y-axis
    fig.add_trace(go.Bar(
        x=dff_maven["Date"],
        y=dff_maven["Bags"],
        name="Bags Ordered",
        yaxis="y2",
        marker_color="orange",
        opacity=0.5
    ))

    # Configure layout for the combined chart
    fig.update_layout(
        title=f"{selected_product} vs. Coffee Market (Candlestick)",
        xaxis=dict(title="Date"),
        yaxis=dict(title="Price (USD)", side="left"),
        yaxis2=dict(
            title="Bags Ordered",
            overlaying="y",
            side="right"
        ),
        hovermode="x unified",  # one hover box for all
        legend=dict(
            x=0.01,
            y=0.01,
            xanchor="left",
            yanchor="bottom",
            bgcolor="rgba(0,0,0,0.6)",
            font=dict(color="white")
        ),
        template="plotly_dark"
    )

    # ---------------------------
    # (C) Compute KPI metrics based on selected date range
    # ---------------------------
    # For Maven data, use the filtered data
    earliest_maven = dff_maven["BagPrice"].iloc[0]
    latest_maven   = dff_maven["BagPrice"].iloc[-1]

    # For Market, slice df_market to the selected date range
    dff_market = df_market[(df_market["Date"] >= pd.to_datetime(start_date)) &
                           (df_market["Date"] <= pd.to_datetime(end_date))].copy()
    if not dff_market.empty:
        dff_market.sort_values("Date", inplace=True)
        earliest_market = dff_market["MarketPrices"].iloc[0]
        latest_market   = dff_market["MarketPrices"].iloc[-1]
    else:
        earliest_market = latest_market = None

    # KPI calculations:
    def pct_growth(start, end):
        if start is None or end is None or start == 0:
            return None
        return ((end - start) / start) * 100.0

    market_growth = pct_growth(earliest_market, latest_market)
    # Price Change for Maven as percentage growth
    price_change = pct_growth(earliest_maven, latest_maven)
    # Latest Diff: percentage difference between final Maven and final Market
    differential = pct_growth(latest_market, latest_maven) if latest_market is not None else None

    # Format KPI strings
    def format_pct(p):
        return f"{p:.2f}%" if p is not None else "N/A"

    kpi_cards = [
        html.Div([
            html.H3("Market Growth"),
            html.P(format_pct(market_growth))
        ], style=_card_style()),
        html.Div([
            html.H3("Price Change"),
            html.P(format_pct(price_change))
        ], style=_card_style()),
        html.Div([
            html.H3("Latest Diff"),
            html.P(f"{format_pct(differential)} vs. Market")
        ], style=_card_style())
    ]

    return fig, kpi_cards

# -------------------------------
# 5) Run the App
# -------------------------------
if __name__ == "__main__":
    app.run_server(debug=True)
