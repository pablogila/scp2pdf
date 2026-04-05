import argparse
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML


VERSION = "v1.0.1"


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
        if not match: return None

        num = int(match.group(1))
        target_text = f"SCP-{str(num).zfill(3)}{match.group(2) or ''}"

        # Dynamically determine the correct hub URL
        url = "https://scp-wiki.wikidot.com/joke-scps" if '-J' in target_text \
            else "https://scp-wiki.wikidot.com/scp-ex" if '-EX' in target_text \
            else "https://scp-wiki.wikidot.com/scp-series" if num < 1000 \
            else f"https://scp-wiki.wikidot.com/scp-series-{(num // 1000) + 1}"

        soup = BeautifulSoup(requests.get(url).text, 'html.parser')
        
        # Locate the exact anchor tag and extract the title text
        for a_tag in soup.find_all('a', string=lambda text: text and text.strip().upper() == target_text):
            parent = a_tag.find_parent('li')
            if parent:
                return parent.get_text().replace(a_tag.text, '', 1).strip(' -–—:\n\r\t')
    except Exception as e:
        print(f"Failed to fetch SCP description: {e}")
    return None


def _parse_acs_class(match):
    """Extracts the class name from an ACS regex match, ignoring placeholder text."""
    if not match: return None
    val = match.group(1).strip().title()
    return val if val.lower() not in ['none', 'n/a', 'pending'] else None


def _process_document_content(raw_html, base_url, fallback_title):
    """Clears Wikidot UI bloat from the HTML and extracts core document metadata."""
    soup = BeautifulSoup(raw_html, 'html.parser')
    content_div = soup.find(id='page-content')
    if not content_div: raise ValueError("Could not find the 'page-content' div.")

    text = content_div.get_text()

    # Extract Core Metadata
    item_match = re.search(r'(?:Item|SCP)\s*#?:\s*([^\n<]+)', text, re.IGNORECASE)
    class_match = re.search(r'(?:Object|Containment) Class:\s*([A-Za-z0-9/\-]+)', text, re.IGNORECASE)
    
    item_number = item_match.group(1).strip() if item_match else fallback_title
    object_class = class_match.group(1).strip().title() if class_match else "N/A"

    # Pull ACS variables
    acs = {
        field.lower(): _parse_acs_class(re.search(fr'{field} Class:\s*([A-Za-z0-9/\-]+)', text, re.IGNORECASE))
        for field in ['Disruption', 'Risk', 'Secondary']
    }

    # Process Citations
    main_citation, supp_citations = "", []

    # Locate the license box, or find it relative to "Cite this page as:"
    license_box = content_div.find('div', class_='licensebox') or \
                  next((n.find_parent('div', class_='collapsible-block') or n.find_parent('div') 
                        for n in content_div.find_all(string=re.compile("Cite this page as:"))), None)

    if license_box:
        for i, bq in enumerate(license_box.find_all('blockquote')):
            for tag in bq.find_all(['img', 'hr']): tag.decompose()
            if i == 0:
                main_citation = str(bq)
            else:
                for bold in bq.find_all(['strong', 'b']): bold.unwrap()
                supp_citations.append(str(bq))
        license_box.decompose()

    # Strip Wikidot UI components
    purge_regex = re.compile(r'(credit|rate-box|page-rate|info-container|anom-bar|author-box|modalbox|wikiwalk)', re.IGNORECASE)
    for el in content_div.find_all(lambda tag: tag.has_attr('class') or tag.has_attr('id')):
        if el.attrs is None: 
            continue
            
        raw_class = el.get('class', [])
        if not isinstance(raw_class, list):
            raw_class = [raw_class] if raw_class else []
            
        css = ' '.join(raw_class) + ' ' + str(el.get('id', ''))
        if purge_regex.search(css): 
            el.decompose()

    # Consolidate specific tag cleanups and URL fixing into a single unified pass
    for el in content_div.find_all(['div', 'a', 'span', 'p', 'img']):
        if not el.parent or el.attrs is None: 
            continue # Skip if already decomposed by a parent or lacks attributes

        el_text = el.get_text(strip=True)
        text_lower = el_text.lower()

        # Remove custom 'X' close buttons
        if el.name == 'div' and el.find('a', string=re.compile(r'^X$')) and len(el_text) < 200:
            el.decompose()
        # Remove edit buttons
        elif el.name in ['div', 'a', 'span'] and ((text_lower == 'edit' and not el.find(['p', 'div', 'table'])) or 'administrator permission is required to edit this page' in text_lower):
            el.decompose()
        # Remove redundant inline metadata headers
        elif el.name == 'p' and re.match(r'^((Item|SCP)\s*#?|(Object|Containment) Class):', el_text, re.IGNORECASE):
            el.decompose()
        # Force absolute Image URLs
        elif el.name == 'img':
            src = el.get('src')
            if src and src.startswith('/'):
                el['src'] = "https://scp-wiki.wikidot.com" + src

    # Clean top-level HRs and author intros
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
                break # Stop at the first real content

    # Process collapsibles safely
    for coll in content_div.find_all('div', class_='collapsible-block'):
        if coll.attrs is None: 
            continue
        unfolded = coll.find('div', class_='collapsible-block-unfolded')
        if not unfolded or unfolded.attrs is None: 
            continue

        if 'style' in unfolded.attrs: 
            del unfolded['style']

        title_text = ""
        folded = coll.find('div', class_='collapsible-block-folded')
        if folded:
            folded_link = folded.find('a', class_='collapsible-block-link')
            if folded_link:
                raw_title = folded_link.get_text(strip=True)
                if not raw_title.lstrip('+ -▷▶\n\r\t').strip().lower().startswith(('show', 'open', 'reveal', 'click')):
                    title_text = raw_title

        unfolded_link = unfolded.find('div', class_='collapsible-block-unfolded-link')
        if unfolded_link: unfolded_link.decompose()

        wrapper = soup.new_tag('div', attrs={'class': 'pdf-collapsible-block'})
        if title_text:
            title_p = soup.new_tag('p', attrs={'class': 'pdf-collapsible-title'})
            strong = soup.new_tag('strong')
            strong.string = title_text
            title_p.append(strong)
            wrapper.append(title_p)

        wrapper.append(unfolded.extract())
        coll.replace_with(wrapper)

    rev_match = re.search(r'page revision:\s*(\d+)', soup.get_text(), re.IGNORECASE)

    return {
        "html": str(content_div),
        "item_number": item_number if len(item_number) <= 30 else fallback_title,
        "object_class": object_class if len(object_class) <= 30 else "CLASSIFIED",
        "acs": acs,
        "main_citation": main_citation,
        "supp_citations": supp_citations,
        "version": rev_match.group(1) if rev_match else "Unknown",
        "is_scp": bool(class_match or item_match or re.search(r'/scp-\d+', base_url.lower()))
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

    # Dynamic target resolution logic
    is_url = target.startswith(("http://", "https://"))
    url = target if is_url else f"https://scp-wiki.wikidot.com/scp-{str(target).zfill(3)}"

    file_prefix = url.split('/')[-1].upper()
    fallback_title = file_prefix.replace('-', ' ') if is_url else f"SCP-{str(target).zfill(3)}"

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
    HTML(string=rendered_html, base_url=base_dir).write_pdf(output_filename)
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
