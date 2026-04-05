# scp2pdf

A Python tool to generate clean, beautifully formatted PDFs from SCP Foundation Wiki entries and tales. It strips away UI elements, extracts relevant metadata, and supports custom themes and images.

<p align="center">
  <img width="40.0%" src="./examples/SCP-035.webp" style="margin-right: 10px;">
  <img width="40.0%" src="./examples/SCP-6003.webp" style="margin-left: 10px;">
</p>


## Installation

Download the repository as a ZIP, or clone it with git:
```bash
git clone https://github.com/pablogila/scp2pdf.git
cd scp2pdf
```

then create a Python virtual environment,
```bash
python -m venv .venv
```

and activate it,
```bash
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
```

and finally install the required dependencies:
```bash
pip install -r requirements.txt
```


## Usage


### Command Line Interface

You can generate a PDF by passing either an SCP number or a full Wikidot URL. For example:

```bash
python scp2pdf.py 035
```

You could also specify custom options with flags like `--theme`, `--image`, `--caption`, and `--outdir`:

```bash
python scp2pdf.py 173 \
  --theme default \
  --image https://upload.wikimedia.org/wikipedia/commons/c/c7/MatthewF1.png \
  --caption "Artistic depiction of SCP-173 by ThyCheshireCat" \
  --outdir "./examples"
```


### Python API

The same custom arguments can be used with the Python API:

```python
import scp2pdf
scp2pdf.generate_pdf(
    target="173",
    theme="default",
    image="https://upload.wikimedia.org/wikipedia/commons/c/c7/MatthewF1.png",
    caption="Artistic depiction of SCP-173 by ThyCheshireCat",
    outdir="./examples"
)
```


## Custom Themes

Themes are controlled by matching HTML and CSS templates stored in the `themes/` directory.
If no theme is specified, the `default` theme will be used.


## Contributing

Do you want to share your own themes or improvements? Feel free to submit a pull request with your contributions! :D


## License

    scp2pdf - Compile SCP entries into stylish PDF reports.
    Copyright (C) 2026 Pablo Gila-Herranz.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

