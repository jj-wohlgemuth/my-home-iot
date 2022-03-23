from dash import Dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html

app = Dash(__name__)
app.layout = html.Div(
    [
        html.Div(id="number_out"),
        html.Hr(),
        dcc.Input(
            id="temp_entry", type="number",
            debounce=False,
            min=0, max=30, step=1,
        )
    ]
)


@app.callback(
    Output("number_out", "children"),
    Input("temp_entry", "value"),
)
def number_render(tval):
    return "number_out: {}".format(tval)


if __name__ == "__main__":
    app.run_server(debug=True)