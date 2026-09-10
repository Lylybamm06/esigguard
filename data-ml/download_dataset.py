"""
Télécharge les 6 fichiers sources du dataset combiné (CEAS_08, Enron, Ling,
Nazario, Nigerian_Fraud, SpamAssassin) dans data-ml/raw/.

Source : https://github.com/rokibulroni/Phishing-Email-Dataset
(compilation de corpus publics utilisés dans la littérature phishing/ML :
CEAS 2008 challenge, Enron-Spam, Ling-Spam, Nazario Phishing Corpus,
419/Nigerian Fraud corpus, SpamAssassin public corpus.)

Usage : python download_dataset.py
"""

import urllib.request
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/rokibulroni/Phishing-Email-Dataset/main/"
FILES = [
    "CEAS_08.csv",
    "Enron.csv",
    "Ling.csv",
    "Nazario.csv",
    "Nigerian_Fraud.csv",
    "SpamAssasin.csv",
]

OUT_DIR = Path(__file__).parent / "raw"


def main():
    OUT_DIR.mkdir(exist_ok=True)
    for filename in FILES:
        dest = OUT_DIR / filename
        if dest.exists():
            print(f"{filename} déjà présent, on saute.")
            continue
        url = BASE_URL + filename
        print(f"Téléchargement de {filename}...")
        urllib.request.urlretrieve(url, dest)
        print(f"  -> {dest} ({dest.stat().st_size / 1_000_000:.1f} Mo)")


if __name__ == "__main__":
    main()
