import sys

print("="*60)
print("Setting up NLP models for StudyMate...")
print("="*60)

# 1. Download spaCy model
print("\n[1/5] Downloading spaCy English model...")
try:
    import spacy
    spacy.cli.download("en_core_web_sm")
    print("✓ spaCy model downloaded")
except Exception as e:
    print(f"✗ spaCy download failed: {e}")

# 2. Download NLTK data
print("\n[2/5] Downloading NLTK data...")
try:
    import nltk
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('wordnet')
    print("✓ NLTK data downloaded")
except Exception as e:
    print(f"✗ NLTK download failed: {e}")

# 3. Download transformer models 
print("\n[3/5] Downloading question generation model...")
print("(This may take 5-10 minutes depending on your internet speed)")
try:
    from transformers import pipeline
    qg_model = pipeline("text2text-generation", model="valhalla/t5-base-qg-hl")
    print("✓ Question generation model downloaded")
except Exception as e:
    print(f"✗ QG model download failed: {e}")

# 4. Download sentence transformer
print("\n[4/5] Downloading sentence transformer...")
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✓ Sentence transformer downloaded")
except Exception as e:
    print(f"✗ Sentence transformer download failed: {e}")

# 5. Test everything
print("\n[5/5] Testing NLP setup...")
try:
    from nlp_processor import FlashcardGenerator
    
    generator = FlashcardGenerator()
    
    # test generation
    test_text = "Python is a high-level programming language. It is widely used for web development."
    cards = generator.generate_flashcards(test_text, max_cards=3)
    
    if cards:
        print("✓ NLP processor working!")
        print(f"\nGenerated {len(cards)} test flashcards:")
        for i, card in enumerate(cards, 1):
            print(f"\n  Card {i}:")
            print(f"    Q: {card['question']}")
            print(f"    A: {card['answer'][:60]}...")
    else:
        print("✗ No flashcards generated")
        
except Exception as e:
    print(f"✗ NLP test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("NLP Setup Complete!")
print("="*60)
print("\nYou can now run the Flask app with advanced NLP:")
print("  python app.py")
print("="*60)