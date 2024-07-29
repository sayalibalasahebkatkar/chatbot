import requests
from bs4 import BeautifulSoup
import html2text
from urllib.parse import urlparse, urljoin,urlunparse
import chromadb


def get_data_from_website(url):
    """
    Retrieve text content and metadata from a given URL.

    Args:
        url (str): The URL to fetch content from.

    Returns:
        tuple: A tuple containing the text content (str), metadata (dict), and a list of same-domain URLs.
    """
    # Get response from the server
    response = requests.get(url)
    if response.status_code == 500:
        print(f"Server error for URL: {url}")
        return None, None, []
    
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Removing js and css code
    for script in soup(["script", "style"]):
        script.extract()

    # Extract text in markdown format
    html = str(soup)
    html2text_instance = html2text.HTML2Text()
    html2text_instance.images_to_alt = True
    html2text_instance.body_width = 0
    html2text_instance.single_line_break = True
    text = html2text_instance.handle(html)

    # Extract page metadata
    try:
        page_title = soup.title.string.strip()
    except:
        page_title = urlparse(url).path[1:].replace("/", "-")
    meta_description = soup.find("meta", attrs={"name": "description"})
    meta_keywords = soup.find("meta", attrs={"name": "keywords"})
    if meta_description:
        description = meta_description.get("content")
    else:
        description = page_title
    if meta_keywords:
        meta_keywords = meta_keywords.get("content")
    else:
        meta_keywords = ""

    metadata = {'title': page_title,
                'url': url,
                'description': description,
                'keywords': meta_keywords}

    # Extract all URLs from the page, ignoring img tags and other irrelevant links

    # Image file extensions
    img_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.ico']
    base_domain = urlparse(url).netloc
    same_domain_urls = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        # Ignore links that are likely not navigational
        if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            continue
        # Ignore links inside img tags
        if link.find_parent('img'):
            continue
        full_url = urljoin(url, href)
        parsed_url = urlparse(full_url)
        url_without_query = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
        img_extension = url_without_query.split('.')[-1]
        if '.'+img_extension in img_extensions:
            continue
        # Check if the URL is valid and has the same domain
        if parsed_url.scheme in ('http', 'https') and parsed_url.netloc == base_domain:
            same_domain_urls.append(full_url)

    return text, metadata, same_domain_urls

def scrape_website_recursively(start_url, max_depth=3):
    """
    Recursively scrape a website and its same-domain URLs.

    Args:
        start_url (str): The starting URL to scrape.
        max_depth (int): Maximum depth for recursive scraping.

    Returns:
        list: A list of tuples, each containing text content and metadata for a URL.
    """
    visited_urls = set()
    results = []
    urls_to_visit = [(start_url, 0)]  # (url, depth)

    while urls_to_visit:
        current_url, depth = urls_to_visit.pop(0)
        
        if current_url in visited_urls or depth > max_depth:
            continue

        visited_urls.add(current_url)
        print(f"Scraping: {current_url}")

        text, metadata, same_domain_urls = get_data_from_website(current_url)
        
        if text and metadata:
            results.append((text, metadata))

        if depth < max_depth:
            for url in same_domain_urls:
                if url not in visited_urls:
                    urls_to_visit.append((url, depth + 1))

    return results

# Example usage
start_url = "https://www.rizzzed.com/"
scraped_data = scrape_website_recursively(start_url)

chroma_client = chromadb.Client()

collection = chroma_client.create_collection(name="my_collection")

for i, (text, metadata) in enumerate(scraped_data, 1):
    collection.add(
    documents=[text],
    ids=[str(i)]
)
    

    # print(f"Page {i}:")
    # print(f"Title: {metadata['title']}")
    # print(f"URL: {metadata['url']}")
    # print(f"Description: {metadata['description']}")
    # print(f"Keywords: {metadata['keywords']}")
    # print(f"Content preview: {text}...")
    # print("\n" + "="*50 + "\n")

results = collection.query(
    query_texts=["what is price of  ghost oversied tshirt"], # Chroma will embed this for you
    n_results=5 # how many results to return
)


print(results)

for i in results['ids'][0]:
    print('--------------','\n','id',i,'\n')
    print(scraped_data[int(i)][0])