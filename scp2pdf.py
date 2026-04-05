import argparse
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML


VERSION = "v1.0.0"


def _fetch_html(url):
    """Fetches the raw HTML content from a given URL."""
    print(f"Fetching content from {url}...")
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def _fetch_scp_title(item_number):
    """Scrapes the SCP Series hub to find the official title of the SCP."""
    try:
        match = re.search(r'(\d+)(-[A-Za-z]+)?', item_number.upper())
        if not match:
            return None

        num = int(match.group(1))
        num_str = str(num).zfill(3)
        suffix = match.group(2) or ""
        target_text = f"SCP-{num_str}{suffix}"

        if '-J' in target_text:
            url = "https://scp-wiki.wikidot.com/joke-scps"
        elif '-EX' in target_text:
            url = "https://scp-wiki.wikidot.com/scp-ex"
        elif num < 1000:
            url = "https://scp-wiki.wikidot.com/scp-series"
        else:
            series = (num // 1000) + 1
            url = f"https://scp-wiki.wikidot.com/scp-series-{series}"

        print(f"Fetching description from {url}...")
        resp = requests.get(url)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for a_tag in soup.find_all('a'):
                if a_tag.text.strip().upper() == target_text:
                    parent_li = a_tag.find_parent('li')
                    if parent_li:
                        text = parent_li.get_text()
                        desc = text.replace(a_tag.text, '', 1).strip(' -–—:\n\r\t')
                        return desc if desc else None
    except Exception as e:
        print(f"Failed to fetch SCP description: {e}")
    return None


def _parse_acs_class(match):
    """Extracts the class name from an ACS regex match, ignoring placeholder text."""
    if not match:
        return None
    val = match.group(1).strip().title()
    if val.lower() not in ['none', 'n/a', 'pending']:
        return val
    return None


def _process_document_content(raw_html, base_url, fallback_title):
    """Clears Wikidot UI bloat from the HTML and extracts core document metadata."""
    soup = BeautifulSoup(raw_html, 'html.parser')
    content_div = soup.find(id='page-content')
    if not content_div:
        raise ValueError("Could not find the 'page-content' div.")

    text = content_div.get_text()

    item_match = re.search(r'(?:Item|SCP)\s*#?:\s*([^\n<]+)', text, re.IGNORECASE)
    class_match = re.search(r'(?:Object|Containment) Class:\s*([A-Za-z0-9/\-]+)', text, re.IGNORECASE)

    is_scp = bool(class_match or item_match or re.search(r'/scp-\d+', base_url.lower()))

    item_number = item_match.group(1).strip() if item_match else fallback_title
    if len(item_number) > 30:
        item_number = fallback_title

    object_class = class_match.group(1).strip().title() if class_match else "N/A"
    if len(object_class) > 30:
        object_class = "CLASSIFIED"

    acs = {
        "disruption": _parse_acs_class(re.search(r'Disruption Class:\s*([A-Za-z0-9/\-]+)', text, re.IGNORECASE)),
        "risk": _parse_acs_class(re.search(r'Risk Class:\s*([A-Za-z0-9/\-]+)', text, re.IGNORECASE)),
        "secondary": _parse_acs_class(re.search(r'Secondary Class:\s*([A-Za-z0-9/\-]+)', text, re.IGNORECASE)),
    }

    rev_match = re.search(r'page revision:\s*(\d+)', soup.get_text(), re.IGNORECASE)
    document_version = rev_match.group(1) if rev_match else "Unknown"

    main_citation = ""
    supp_citations = []
    license_box = content_div.find('div', class_='licensebox')

    if not license_box:
        for text_node in content_div.find_all(string=re.compile("Cite this page as:")):
            parent = text_node.find_parent('div', class_='collapsible-block') or text_node.find_parent('div')
            if parent:
                license_box = parent
                break

    if license_box:
        bqs = license_box.find_all('blockquote')
        if bqs:
            # First blockquote is the main document citation
            first_bq = bqs[0]
            for img in first_bq.find_all('img'):
                img.decompose()
            for hr in first_bq.find_all('hr'):
                hr.decompose()
            main_citation = str(first_bq)
            # Subsequent blockquotes as supplementary files
            for bq in bqs[1:]:
                for img in bq.find_all('img'):
                    img.decompose()
                for hr in bq.find_all('hr'):
                    hr.decompose()
                # Unwrap bold tags to render as plain text
                for bold in bq.find_all(['strong', 'b']):
                    bold.unwrap()
                supp_citations.append(str(bq))
                
        license_box.decompose()

    purge_classes = r'(credit|rate-box|page-rate|info-container|anom-bar|author-box|modalbox|wikiwalk)'
    for element in content_div.find_all(['div', 'span', 'p']):
        if element.attrs is None:
            continue

        raw_class = element.get('class', [])
        css_classes = ' '.join(raw_class if isinstance(raw_class, list) else [raw_class]).lower()
        css_id = element.get('id', '').lower()

        if re.search(purge_classes, css_classes) or re.search(purge_classes, css_id):
            element.decompose()

    for child in content_div.find_all('div'):
        if child.attrs is None:
            continue
        child_text = child.get_text(strip=True)
        if child.find('a', string=re.compile(r'^X$')) and len(child_text) < 200:
            child.decompose()

    for btn in content_div.find_all(['div', 'a', 'span']):
        if btn.attrs is None:
            continue
        if btn.get_text(strip=True).lower() == 'edit' and not btn.find(['p', 'div', 'table']):
            btn.decompose()

    for p in content_div.find_all('p'):
        if p.attrs is None:
            continue
        p_text = p.get_text(strip=True)
        if re.match(r'^(Item|SCP)\s*#?:', p_text, re.IGNORECASE) or re.match(r'^(Object|Containment) Class:', p_text, re.IGNORECASE):
            p.decompose()

    for child in content_div.find_all(recursive=False):
        if child.attrs is None:
            continue
        if child.name == 'hr':
            child.decompose()
        elif child.name in ['p', 'div', 'blockquote', 'table']:
            child_text = child.get_text(strip=True)
            if child_text and len(child_text) < 100 and (child_text.startswith('by ') or ': X' in child_text):
                child.decompose()
            elif child_text:
                break

    for collapsible in content_div.find_all('div', class_='collapsible-block'):
        if collapsible.attrs is None:
            continue

        folded = collapsible.find('div', class_='collapsible-block-folded')
        unfolded = collapsible.find('div', class_='collapsible-block-unfolded')

        if unfolded:
            if unfolded.attrs and 'style' in unfolded.attrs:
                del unfolded['style']

            title_text = ""
            if folded:
                link = folded.find('a', class_='collapsible-block-link')
                if link:
                    raw_title = link.get_text(strip=True)
                    clean_title = raw_title.lstrip('+ -▷▶\n\r\t').strip().lower()
                    if not clean_title.startswith(('show', 'open', 'reveal', 'click')):
                        title_text = raw_title

            unfolded_link = unfolded.find('div', class_='collapsible-block-unfolded-link')
            if unfolded_link:
                unfolded_link.decompose()

            extracted_unfolded = unfolded.extract()
            wrapper = soup.new_tag('div', attrs={'class': 'pdf-collapsible-block'})

            if title_text:
                title_p = soup.new_tag('p', attrs={'class': 'pdf-collapsible-title'})
                strong_tag = soup.new_tag('strong')
                strong_tag.string = title_text
                title_p.append(strong_tag)
                wrapper.append(title_p)

            wrapper.append(extracted_unfolded)
            collapsible.replace_with(wrapper)

    for img in content_div.find_all('img'):
        if img.attrs is None:
            continue
        if img.has_attr('src') and img['src'].startswith('/'):
            img['src'] = "https://scp-wiki.wikidot.com" + img['src']

    return {
        "html": str(content_div),
        "item_number": item_number,
        "object_class": object_class,
        "acs": acs,
        "main_citation": main_citation,
        "supp_citations": supp_citations,
        "version": document_version,
        "is_scp": is_scp
    }


def generate_pdf(target, theme="default", image=None, caption=None, outdir=None):
    """
    Compiles an SCP entry or tale into a styled PDF.

    target (str): SCP number (e.g., '035') or full Wikidot URL.
    theme (str): Optional name of the theme to load from the themes/ directory.
    image (str): Optional URL or local path to a custom header image.
    caption (str): Optional caption for the custom image.
    outdir (str): Optional directory path to save the generated PDF.
    """
    print(f"Processing SCP {target}...")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    themes_dir = os.path.join(base_dir, 'themes')
    css_path = os.path.join(themes_dir, f"{theme}.css")
    html_template = f"{theme}.html"

    if not os.path.exists(css_path) or not os.path.exists(os.path.join(themes_dir, html_template)):
        raise FileNotFoundError(f"Theme '{theme}' files not found in {themes_dir}")

    if image and not image.startswith(('http://', 'https://')):
        image = f"file://{os.path.abspath(image)}"

    if target.startswith("http://") or target.startswith("https://"):
        url = target
        fallback_title = url.split('/')[-1].replace('-', ' ').upper()
        file_prefix = url.split('/')[-1].upper()
    else:
        formatted_number = str(target).zfill(3)
        url = f"https://scp-wiki.wikidot.com/scp-{formatted_number}"
        fallback_title = f"SCP-{formatted_number}"
        file_prefix = f"SCP-{formatted_number}"

    outdir = outdir or os.path.join(os.getcwd(), "SCP")
    os.makedirs(outdir, exist_ok=True)
    output_filename = os.path.join(outdir, f"{file_prefix}.pdf")

    raw_html = _fetch_html(url)
    doc_data = _process_document_content(raw_html, url, fallback_title)

    scp_name = _fetch_scp_title(doc_data["item_number"]) if doc_data["is_scp"] else None

    with open(css_path, 'r', encoding='utf-8') as f:
        css_content = f.read()

    env = Environment(loader=FileSystemLoader(themes_dir))
    template = env.get_template(html_template)

    rendered_html = template.render(
        item_number=doc_data["item_number"],
        object_class=doc_data["object_class"],
        scp_name=scp_name,
        acs=doc_data["acs"],
        css_content=css_content,
        content=doc_data["html"],
        image=image,
        caption=caption,
        main_citation=doc_data["main_citation"],
        supp_citations=doc_data["supp_citations"],
        source_url=url,
        is_scp=doc_data["is_scp"],
        document_version=doc_data["version"],
        retrieval_date=datetime.now().strftime("%Y-%m-%d"),
        scp2pdf_version=VERSION
    )

    print(f"Generating PDF...")
    HTML(string=rendered_html).write_pdf(output_filename)
    print(f"Saved as {output_filename}")

    return output_filename

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a printable PDF for an SCP entry or tale.")
    parser.add_argument("target", help="The SCP number (e.g., '035') or URL")
    parser.add_argument("--theme", default="default", help="Name of the theme in the themes/ folder")
    parser.add_argument("--image", default=None, help="URL or local path to add a custom image")
    parser.add_argument("--caption", default=None, help="Caption for the custom image")
    parser.add_argument("--outdir", default=None, help="Folder to save the generated PDF")

    args = parser.parse_args()

    try:
        generate_pdf(
            target=args.target, 
            theme=args.theme,
            image=args.image,
            caption=args.caption,
            outdir=args.outdir
        )
    except Exception as e:
        print(f"Error: {e}")
