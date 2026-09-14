"""Regenerate the corpus on disk: python -m meridian.corpus"""

from meridian.catalog import load_catalog
from meridian.corpus import generate_corpus
from meridian.corpus.models import CORPUS_DIR, write_corpus


def main() -> None:
    catalog = load_catalog()
    documents = generate_corpus(catalog)
    write_corpus(documents)
    print(f"wrote {len(documents)} documents to {CORPUS_DIR}")


if __name__ == "__main__":
    main()
