import spacy
import nltk
from transformers import pipeline
from sentence_transformers import SentenceTransformer
import re
from typing import List, Dict
import warnings
warnings.filterwarnings('ignore')

class FlashcardGenerator:
    def __init__(self):
        """Initialize NLP models"""
        print("Initializing NLP models...")
        
        try:
            # load spacy model for NER and dependency parsing
            self.nlp = spacy.load("en_core_web_sm")
            print("✓ SpaCy model loaded")
        except:
            print("⚠ SpaCy model not found. Run: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        try:
            # download NLTK data
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
            from nltk.corpus import stopwords
            self.stopwords = set(stopwords.words('english'))
            print("✓ NLTK initialized")
        except:
            print("⚠ NLTK initialization failed")
            self.stopwords = set()
        
        try:
            # question generation model
            self.qg_model = pipeline("text2text-generation", model="valhalla/t5-base-qg-hl")
            print("✓ Question generation model loaded")
        except Exception as e:
            print(f"⚠ Question generation model failed: {e}")
            self.qg_model = None
        
        try:
            # sentence transformer for semantic similarity
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✓ Sentence transformer loaded")
        except:
            print("⚠ Sentence transformer failed")
            self.sentence_model = None
        
        print("NLP initialization complete!")
    
    def generate_flashcards(self, text: str, max_cards: int = 15) -> List[Dict]:
        """
        Generate flashcards using multiple NLP techniques
        """
        print(f"Generating flashcards from {len(text)} characters of text...")
        
        all_cards = []
        
        # method 1: definition-based cards
        definition_cards = self._extract_definitions(text)
        all_cards.extend(definition_cards)
        print(f"Generated {len(definition_cards)} definition cards")
        
        # method 2: entity-based cards
        if self.nlp:
            entity_cards = self._extract_entities(text)
            all_cards.extend(entity_cards)
            print(f"Generated {len(entity_cards)} entity cards")
        
        # method 3: key concept cards
        concept_cards = self._extract_key_concepts(text)
        all_cards.extend(concept_cards)
        print(f"Generated {len(concept_cards)} concept cards")
        
        # method 4: AI-generated questions
        if self.qg_model:
            ai_cards = self._generate_ai_questions(text)
            all_cards.extend(ai_cards)
            print(f"Generated {len(ai_cards)} AI cards")
        
        # method 5: relationship cards
        if self.nlp:
            relation_cards = self._extract_relationships(text)
            all_cards.extend(relation_cards)
            print(f"Generated {len(relation_cards)} relationship cards")
        
        # remove duplicates and rank by quality
        unique_cards = self._deduplicate_cards(all_cards)
        ranked_cards = self._rank_cards(unique_cards)
        
        # return top cards
        final_cards = ranked_cards[:max_cards]
        print(f"Returning {len(final_cards)} flashcards")
        
        return final_cards
    
    def _extract_definitions(self, text: str) -> List[Dict]:
        """Extract definition-style flashcards"""
        cards = []
        
        # patterns for definitions
        patterns = [
            r'(.+?)\s+is\s+(?:a|an|the)?\s*(.+?)[\.\,\;]',
            r'(.+?)\s+are\s+(.+?)[\.\,\;]',
            r'(.+?)\s+refers to\s+(.+?)[\.\,\;]',
            r'(.+?)\s+means\s+(.+?)[\.\,\;]',
            r'(.+?)\s+can be defined as\s+(.+?)[\.\,\;]',
            r'The term\s+(.+?)\s+means\s+(.+?)[\.\,\;]',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                term = match.group(1).strip()
                definition = match.group(2).strip()
                
                # clean up
                if len(term) > 3 and len(definition) > 10 and len(term) < 100:
                    cards.append({
                        'question': f'What is {term}?',
                        'answer': definition,
                        'type': 'definition',
                        'confidence': 0.9
                    })
        
        return cards
    
    def _extract_entities(self, text: str) -> List[Dict]:
        """Extract named entity flashcards"""
        cards = []
        
        if not self.nlp:
            return cards
        
        doc = self.nlp(text)
        
        # group entities by type
        entities_by_type = {}
        for ent in doc.ents:
            if ent.label_ not in entities_by_type:
                entities_by_type[ent.label_] = []
            entities_by_type[ent.label_].append(ent.text)
        
        # create cards for important entity types
        for ent_type, entities in entities_by_type.items():
            if len(entities) > 0:
                # create "What is X?" cards
                for entity in entities[:3]:  # limit per type
                    # find context sentence
                    context = self._get_entity_context(text, entity)
                    if context:
                        cards.append({
                            'question': f'What is {entity}?',
                            'answer': context,
                            'type': 'entity',
                            'confidence': 0.8
                        })
        
        return cards
    
    def _extract_key_concepts(self, text: str) -> List[Dict]:
        """Extract key concepts using keyword extraction"""
        cards = []
        
        # split into sentences
        sentences = nltk.sent_tokenize(text)
        
        for sentence in sentences:
            if len(sentence) < 20 or len(sentence) > 300:
                continue
            
            # check if sentence contains important keywords
            important_words = ['important', 'key', 'crucial', 'significant', 
                             'note that', 'remember', 'main', 'primary']
            
            if any(word in sentence.lower() for word in important_words):
                # extract the main concept
                words = nltk.word_tokenize(sentence)
                # remove stopwords
                keywords = [w for w in words if w.lower() not in self.stopwords and len(w) > 3]
                
                if keywords:
                    concept = ' '.join(keywords[:3])
                    cards.append({
                        'question': f'What is important about {concept}?',
                        'answer': sentence,
                        'type': 'concept',
                        'confidence': 0.7
                    })
        
        return cards[:5]  # limit key concept cards
    
    def _generate_ai_questions(self, text: str) -> List[Dict]:
        """Use transformer model to generate questions"""
        cards = []
        
        if not self.qg_model:
            return cards
        
        # split text into chunks
        sentences = nltk.sent_tokenize(text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < 512:  # model max length
                current_chunk += " " + sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # generate questions for each chunk
        for chunk in chunks[:3]:  # limit to first 3 chunks
            try:
                # highlight important parts (simple approach)
                highlighted = self._highlight_text(chunk)
                result = self.qg_model(highlighted, max_length=64, num_return_sequences=2)
                
                for item in result:
                    question = item['generated_text']
                    if question and '?' in question:
                        cards.append({
                            'question': question.strip(),
                            'answer': chunk,
                            'type': 'ai_generated',
                            'confidence': 0.85
                        })
            except Exception as e:
                print(f"AI question generation error: {e}")
                continue
        
        return cards
    
    def _extract_relationships(self, text: str) -> List[Dict]:
        """Extract relationship-based flashcards"""
        cards = []
        
        if not self.nlp:
            return cards
        
        doc = self.nlp(text)
        
        # look for cause-effect relationships
        for sent in doc.sents:
            sent_text = sent.text
            
            # cause-effect patterns
            if 'because' in sent_text.lower():
                parts = re.split(r'because', sent_text, flags=re.IGNORECASE)
                if len(parts) == 2:
                    cards.append({
                        'question': f'Why {parts[0].strip()}?',
                        'answer': f'Because {parts[1].strip()}',
                        'type': 'relationship',
                        'confidence': 0.75
                    })
            
            elif 'therefore' in sent_text.lower() or 'thus' in sent_text.lower():
                cards.append({
                    'question': 'What is the consequence?',
                    'answer': sent_text,
                    'type': 'relationship',
                    'confidence': 0.7
                })
        
        return cards[:3]  # limit relationship cards
    
    def _get_entity_context(self, text: str, entity: str) -> str:
        """Get the sentence containing the entity"""
        sentences = nltk.sent_tokenize(text)
        for sentence in sentences:
            if entity in sentence:
                return sentence
        return ""
    
    def _highlight_text(self, text: str) -> str:
        """Add highlighting for question generation"""
        # simple approach: highlight first noun phrase
        if self.nlp:
            doc = self.nlp(text)
            for chunk in doc.noun_chunks:
                return text.replace(chunk.text, f"<hl> {chunk.text} <hl>", 1)
        return text
    
    def _deduplicate_cards(self, cards: List[Dict]) -> List[Dict]:
        """Remove duplicate or very similar flashcards"""
        if not cards or not self.sentence_model:
            return cards
        
        unique_cards = []
        seen_questions = set()
        
        for card in cards:
            question_lower = card['question'].lower().strip()
            
            # exact duplicate check
            if question_lower in seen_questions:
                continue
            
            # add to unique cards
            unique_cards.append(card)
            seen_questions.add(question_lower)
        
        return unique_cards
    
    def _rank_cards(self, cards: List[Dict]) -> List[Dict]:
        """Rank flashcards by quality"""
        # sort by confidence score and type priority
        type_priority = {
            'definition': 4,
            'ai_generated': 3,
            'entity': 2,
            'concept': 2,
            'relationship': 1
        }
        
        def card_score(card):
            type_score = type_priority.get(card.get('type', 'other'), 0)
            confidence = card.get('confidence', 0.5)
            return (type_score * confidence)
        
        ranked = sorted(cards, key=card_score, reverse=True)
        return ranked

# global instance
_generator = None

def get_generator():
    """Get or create the global flashcard generator"""
    global _generator
    if _generator is None:
        _generator = FlashcardGenerator()
    return _generator

def generate_flashcards(text: str, max_cards: int = 15) -> List[Dict]:
    """
    Main function to generate flashcards
    """
    generator = get_generator()
    cards = generator.generate_flashcards(text, max_cards)
    
    # convert to simple format
    simple_cards = []
    for card in cards:
        simple_cards.append({
            'question': card['question'],
            'answer': card['answer']
        })
    
    return simple_cards