import marimo

__generated_with = "0.16.5"
app = marimo.App(width="full", app_title="HorusBinary v3 Playground")


@app.cell(hide_code=True)
def _():
    import micropip
    import json
    import marimo as mo
    PATH_TO_HORUS_ASN1 = mo.notebook_location() / "public" / "HorusBinaryV3.asn1"
    return micropip, mo


@app.cell(hide_code=True)
async def _(micropip, mo):

    await micropip.install("asn1tools")
    await micropip.install("wcwidth")
    await micropip.install(str(mo.notebook_location() / "public" / "blockdiag-3.3.0-py3-none-any.whl" ))
    await micropip.install("sqlite3")
    await micropip.install("nwdiag")
    return


@app.cell(hide_code=True)
def _(mo):
    import requests
    try:
        ASN1_DEF = requests.get(str(mo.notebook_location() / "public" / "HorusBinaryV3.asn1" )).text
    except:
        ASN1_DEF = open(str(mo.notebook_location() / "public" / "HorusBinaryV3.asn1"),"r").read()
    from packetdiag import parser, builder, drawer
    return ASN1_DEF, builder, drawer, parser


@app.cell
def _(mo):
    mo.md(
        r"""
    ## HorusBinaryV3 ASN.1
    ### Importing, Compiling and Encoding with the ASN.1 codec
    """
    )
    return


@app.cell(hide_code=True)
def _(ASN1_DEF, mo):
    MAX_HEIGHT=1000
    asn1_editor = mo.ui.code_editor(value=ASN1_DEF,language="asn1",label="HorusBinaryV3.asn1", max_height=MAX_HEIGHT,min_height=MAX_HEIGHT)

    editor = mo.ui.code_editor("""
    {
        "payloadCallsign": "VK3FUR",
        "sequenceNumber": 1234,

        "timeOfDaySeconds": 9001,
        "latitude": 89_94589,
        "longitude": -23_34458,
        "altitudeMeters": 23000,

        "velocityHorizontalKilometersPerHour": 200,
        "gnssSatellitesVisible": 18,

        "temperatureCelsius-x10": {
            "internal": 100,
            "external": 200
        },
        "milliVolts": {
            "battery": 2300
        },

        "ascentRateCentimetersPerSecond": 1080,
        "humidityPercentage": 10,

        "extraSensors": [
            {
                "name": "rad", 
                "values": ("horusInt", [1,2,3])
            }
        ],

        "gnssPowerSaveState": "tracking",
    }
    """,language="python",label="Data to encode", max_height=MAX_HEIGHT,min_height=MAX_HEIGHT)


    the_stack = mo.hstack([ asn1_editor.style({"width":"50%"}), editor.style({"width":"50%"})])
    the_stack
    return asn1_editor, editor


@app.cell(hide_code=True)
def _(editor, mo):
    return_value=mo.md("")
    exec_data={}


    try:
        data = eval( editor.value)
    except Exception as e:
        data = {"payloadCallsign": "VK3FUR",
    "sequenceNumber": 1234,

    "timeOfDaySeconds": 9001,
    "latitude": 123.945893903,
    "longitude": -23.344589499,
    "altitudeMeters": 23000}
        return_value=mo.vstack([mo.md("""
    <p style="color:red;font-size:12pt">Error parsing encoding data. Ensure that you have a valid python dictionary. Will use demo data for the time being.</p>
    """),mo.inspect(e)])
    return_value
    return (data,)


@app.cell(hide_code=True)
def _(mo):
    mo.ui.code_editor(disabled=True,value="""import asn1tools
    HorusBinaryV3 = asn1tools.compile_string(asn1_editor.value, codec="uper")
    output = HorusBinaryV3.encode('Telemetry', data, check_constraints=True, check_types=True)""",language="python",min_height=1)
    return


@app.cell
def _(asn1_editor, data, mo):
    cell_out=None
    try:
        import asn1tools
        HorusBinaryV3 = asn1tools.compile_string(asn1_editor.value, codec="uper")
        output = HorusBinaryV3.encode('Telemetry', data,check_constraints=True,check_types=True)
    except Exception as e:
        output = b''
        cell_out = mo.inspect(e).callout("danger")
    cell_out
    return HorusBinaryV3, asn1tools, output


@app.cell
def hexout(mo, output):
    output.hex()
    len(output)
    mo.show_code()
    return


@app.cell(hide_code=True)
def _(mo, output):
    mo.md(
        f"""
    |    |    |
    | -- | -- |
    | <p align="left"> **Payload data** </p> | `{output.hex()}` |
    | <p align="left"> **Payload bytes** </p> | <p align="left"> {len(output)} </p> |

    ### Packet layout
    """
    )
    return


@app.cell(hide_code=True)
def _(HorusBinaryV3, asn1tools, builder, data, drawer, mo, parser):
    import inspect
    class VizEncoder(asn1tools.codecs.uper.Encoder):
        def __init__(self, *args, **kwargs):
            self.map = []
            self.last_frame = None
            super().__init__(*args, **kwargs)

        def inspect(self, calling_frame):

            try:
                label = calling_frame['self'].type_label()
            except:
                label = f"{calling_frame['self'].name} ({calling_frame['self'].type_name})"

            if inspect.stack()[2] != self.last_frame:
                self.last_frame=inspect.stack()[2]
                _str = ""
                if 'data' in calling_frame:
                    if type(calling_frame['data']) in [str,int, float]:
                        _str = str(calling_frame['data'])
                    elif type(calling_frame['data']) in [bytes, bytearray]:
                        _str = calling_frame['data'].hex()
                    else:
                        try:
                            _str = str(len(calling_frame['data']))
                        except:
                            pass
                else:
                    try:
                        _str = str(len(calling_frame.values()))
                    except:
                        pass
                label = f"{label}\\n{_str}"
                if len(self.map)>0:
                    self.map[-1]["end"] = self.number_of_bits-1
                    self.map.append({
                        "label": label,
                        "start": self.number_of_bits
                    })
                else:
                    self.map.append({
                        "label": label,
                        "start": 0
                    })

        def append_bit(self, *args, **kwargs):      
            frame = inspect.currentframe()
            calling_frame=frame.f_back.f_locals
            self.inspect(calling_frame)
            super().append_bit(*args, **kwargs)


        def append_non_negative_binary_integer(self, *args, **kwargs):
            frame = inspect.currentframe()
            calling_frame=frame.f_back.f_locals
            if type(frame.f_back.f_locals['self']) != VizEncoder:
                self.inspect(calling_frame)
                super().append_non_negative_binary_integer(*args, **kwargs)
            else:
                try_back = frame.f_back
                for x in range(0,8):
                    if type(try_back.f_locals['self']) != VizEncoder:
                        self.inspect(try_back.f_locals)
                        super().append_non_negative_binary_integer(*args, **kwargs)
                        return
                    else:
                        try_back = try_back.f_back

        def as_bytearray(self, *args, **kwargs):
            if len(self.map)>0:
                    self.map[-1]["end"] = self.number_of_bits-1
            return super().as_bytearray(*args, **kwargs)
    cellout = None

    try:
        encoderviz = VizEncoder()
        HorusBinaryV3._types['Telemetry']._type.encode(data,encoderviz)
        output_viz = encoderviz.as_bytearray()
    except Exception as e:
        cellout = mo.inspect(e).callout("danger")
        mo.stop(True, cellout)

    lines = """
    {
      colwidth = 32
      node_height = 80
      node_width = 38

    """


    for x in encoderviz.map:
        label = x['label'].replace("(",' \\n(')
        output_viz_bytes = output_viz[x['start']//8:x['end']//8+1]
        bin_data = "".join([format(x,'08b') for x in output_viz_bytes])
        offset = x['start'] % 8
        end_offset = 7-(x['end'] % 8)
        lines += f"  {x['start']}-{x['end']}: {label}\\n{bin_data[offset:-end_offset]}\n"
    lines += """
    }
    """


    try:
        tree = parser.parse_string(lines)
        diagram = builder.ScreenNodeBuilder(tree)

        draw = drawer.DiagramDraw("SVG", diagram.build(tree),
                                          ignore_pil=True)
        draw.draw()
        import base64
        output_64 = base64.b64encode(draw.save().encode()).decode()

    except Exception as e:
        cellout = mo.inspect(e).callout("danger")
        mo.stop(True, cellout)
    mo.accordion(items={"Click to show/hide payload layout": mo.image(src=f"data:image/svg+xml;base64,{output_64}")},lazy=False)
    return


@app.cell
def _(mo):
    mo.md(r"""### Decoding""")
    return


@app.cell(hide_code=True)
def _(mo, output):
    text = mo.ui.text(placeholder="Hex data 7bba....", label="Telemetery to decode (in hex): ",value=output.hex(),full_width=True)
    mo.vstack([text])
    return (text,)


@app.cell
def _(mo):
    mo.ui.code_editor("""HorusBinaryV3.decode('Telemetry', bytes.fromhex(text.value), check_constraints=True)""",disabled=True,language="python",min_height=1)
    return


@app.cell(hide_code=True)
def _(HorusBinaryV3, mo, text):
    output_decoded = None
    try:
        decoded = HorusBinaryV3.decode('Telemetry', bytes.fromhex(text.value),check_constraints=True)
        output_decoded = mo.json(decoded)
    except Exception as e:
        output_decoded = mo.inspect(e).callout("danger")
    output_decoded
    return


if __name__ == "__main__":
    app.run()
