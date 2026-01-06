import os
import json
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_json(file_path: str):
    """
    Load structured JSON data and split into chunks.
    Each section_desc becomes a Document with metadata.
    """
    docs = []
    filename = os.path.basename(file_path)
    source_name = os.path.splitext(filename)[0]  # remove extension

    # Load JSON
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        section_desc = item.get("section_desc", "").strip()
        if not section_desc:
            continue  # skip empty sections

        # Create Document with metadata
        docs.append(Document(
            page_content=section_desc,
            metadata={
                "chapter": item.get("chapter", ""),
                "chapter_title": item.get("chapter_title", ""),
                "section": item.get("section", ""),
                "section_title": item.get("section_title", "")
            }
        ))

    # Chunk documents
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=150)
    split_docs = splitter.split_documents(docs)

    return split_docs


# # Example usage
# if __name__ == "__main__":
#     chunks = load_json(r"final_data/bns.json")
#     print(f"Total chunks created: {len(chunks)}")
#     print("\npage content::",chunks[0].page_content)
#     print("\nmetadata::",chunks[0].metadata)
