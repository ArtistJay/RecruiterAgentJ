import os
import json
import chromadb
from sentence_transformers import SentenceTransformer

def seed():
    # Setup ChromaDB (local persistent storage)
    db_path = "db/chroma"
    os.makedirs(db_path, exist_ok=True)
    client = chromadb.PersistentClient(path=db_path)
    
    # Delete old collection if exists (clean re-seed)
    try:
        client.delete_collection("candidates")
        print("🗑️  Cleared old collection")
    except:
        pass
    
    collection = client.create_collection(name="candidates")
    
    # Load embedding model to GPU
    device = "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda"
    except:
        pass
    print(f"🎸 Loading SentenceTransformer on {device.upper()}...")
    model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
    print("   Model loaded ✅\n")
    
    candidate_dir = "data/candidates"
    files = sorted([f for f in os.listdir(candidate_dir) if f.endswith(".json")])
    
    if not files:
        print("❌ No candidate files found! Run generate_candidates.py first.")
        return
    
    ids = []
    embeddings = []
    metadatas = []
    documents = []
    
    for filename in files:
        filepath = os.path.join(candidate_dir, filename)
        with open(filepath, "r") as f:
            data = json.load(f)
        
        # Build searchable text from profile
        skills = ", ".join(data.get("skills", []))
        edu = data.get("education", {})
        if isinstance(edu, dict):
            edu_text = f"{edu.get('degree', '')} in {edu.get('field', '')} from {edu.get('university', '')}"
        else:
            edu_text = str(edu)
        
        searchable = (
            f"Role: {data.get('current_role', 'Unknown')}. "
            f"Skills: {skills}. "
            f"Experience: {data.get('years_experience', 'Unknown')} years. "
            f"{data.get('experience_summary', '')} "
            f"Education: {edu_text}. "
            f"Goals: {data.get('career_goals', '')}"
        )
        
        embedding = model.encode(searchable).tolist()
        
        ids.append(data.get("candidate_id", filename))
        embeddings.append(embedding)
        metadatas.append({
            "name": data.get("name", "Unknown"),
            "role": data.get("current_role", "Unknown"),
            "file": filename,
            "years_exp": str(data.get("years_experience", 0)),
            "skills": skills
        })
        documents.append(searchable)
        print(f"  📦 {data.get('name', 'Unknown'):30s} | {data.get('current_role', 'Unknown')}")
    
    # Batch add (much faster than one-by-one)
    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents
    )
    
    print(f"\n🔥 {len(ids)} candidates indexed in ChromaDB at {db_path}/")
    print(f"   Collection: 'candidates'")
    print(f"   Ready for vector search!")


if __name__ == "__main__":
    seed()
