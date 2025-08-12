import requests
from bs4 import BeautifulSoup
import random
from lxml import html
import xml.etree.ElementTree as ET
from zss import simple_distance, Node
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns
def load_urls_from_xml(xml_file):
    """Parse XML and return a list of (url, old_hash)."""
    tree = ET.parse(xml_file)
    root = tree.getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = []
    for url_node in root.findall("sm:url", ns):
        loc = url_node.find("sm:loc", ns).text
        urls.append(loc)
    return urls


def fetch_html(url):
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.text
    except:
        return None

def extract_dom_paths(html_text):
    tree = html.fromstring(html_text)
    paths = []
    for el in tree.iter(): #iterate over every dom element
        # build simple path: tag.class#id
        tag = el.tag #get tag name ie div, p, ul
        cls = el.get("class", "") #get class if it has one
        ident = el.get("id", "") #get the id if it has one
        path = f"{tag}.{cls}#{ident}" #add elements to a string
        paths.append(path) #add each element to a list "div.main-content#page" or p.article-paragraph#
    return paths



def build_tree(lxml_node):
    n = Node(lxml_node.tag)
    for child in lxml_node:
        n.addkid(build_tree(child))
    return n

def dom_distance(html_a, html_b):
    tree_a = build_tree(html.fromstring(html_a))
    tree_b = build_tree(html.fromstring(html_b))
    return simple_distance(tree_a, tree_b)

def get_top_similar_pairs(sim_matrix, urls, top_n=10):
    n = sim_matrix.shape[0]
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):  # upper triangle only
            pairs.append((sim_matrix[i, j], i, j))
    
    # Sort by similarity (highest first)
    pairs.sort(reverse=True, key=lambda x: x[0])

    # Print top N pairs
    print(f"\nTop {top_n} Most Similar Page Pairs:")
    for score, i, j in pairs[:top_n]:
        print(f"[{score:.3f}] P{i} <-> P{j}")
        print(f"   {urls[i]}")
        print(f"   {urls[j]}")

def main():

    size = 100
    urls = load_urls_from_xml("../get_diffs_solutions/uoregon_urls_test.xml")
    html_list = [fetch_html(url) for url in urls[:size] if url]
    dom_paths = [extract_dom_paths(html) for html in html_list]
    # pairwise distances for clustering
    n = len(html_list)
    corpus = [" ".join(paths) for paths in dom_paths]
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(corpus)
    similarity_matrix = cosine_similarity(X)
    print(similarity_matrix)

    n = len(html_list)                 # how many pages you really have
    label_count = min(n, 50)           # don’t label more than 50 – keeps it readable

    plt.figure(figsize=(12, 10))       # adjust as needed
    sns.heatmap(
        similarity_matrix[:n, :n],     # square sub-matrix for the pages you have
        cmap="viridis",
        vmin=0, vmax=1,                # full similarity range
        square=True,                   # keep cells square
        cbar_kws={"label": "cosine similarity"},
        xticklabels=[f"P{i}" for i in range(label_count)],
        yticklabels=[f"P{i}" for i in range(label_count)],
        annot=False                    # turn on if n is very small
    )
    plt.title(f"DOM-structure similarity – first {n} pages")
    plt.tight_layout()
    plt.show()

    """
    X_2d = PCA(n_components=2).fit_transform(X.toarray())
    plt.figure(figsize=(6, 5))
    plt.scatter(X_2d[:, 0], X_2d[:, 1], s=size, c="blue")
    for i, url in enumerate(urls[:size]):
        plt.text(X_2d[i, 0] + 0.01, X_2d[i, 1] + 0.01, f"P{i}", fontsize=9)
    plt.title("PCA of DOM Template Features")
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.show()
    """

    get_top_similar_pairs(similarity_matrix, urls[:size], 100)

if __name__ == "__main__":
    main()
