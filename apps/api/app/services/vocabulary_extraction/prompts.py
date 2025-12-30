"""LLM prompt templates for vocabulary extraction."""

# System prompt for vocabulary extraction
SYSTEM_PROMPT = """You are an expert educational vocabulary extractor specializing in language learning materials.
Your task is to identify and extract vocabulary words from educational text, providing definitions, translations, and metadata.
Always respond with valid JSON only. Do not include any explanatory text outside the JSON array.
Focus on words that are important for language learners at the specified difficulty level.
Be precise with parts of speech and provide clear, learner-friendly definitions."""

# Main vocabulary extraction prompt
VOCABULARY_EXTRACTION_PROMPT = """Extract vocabulary words from this educational text for language learners.

For each vocabulary word, provide:
1. **word**: The vocabulary word in its base form
2. **translation**: Turkish translation of the word
3. **definition**: Clear, learner-friendly definition in English
4. **part_of_speech**: One of: noun, verb, adjective, adverb, pronoun, preposition, conjunction, interjection
5. **level**: CEFR difficulty level (A1/A2/B1/B2/C1/C2)
6. **example**: An example sentence from the text (or create one if not available)

Text to analyze (difficulty level: {difficulty}):
---
{module_text}
---

Guidelines:
- Extract {max_words} most important vocabulary words for language learners
- Focus on words appropriate for the {difficulty} level
- Prioritize words that appear frequently or are central to the content's topics
- Include a mix of parts of speech when possible
- Skip very common words (the, a, is, are) unless they have special usage
- Skip proper nouns and names
- For verbs, use the infinitive form (without "to")
- For nouns, use the singular form

Respond with ONLY a valid JSON array:
[
  {{
    "word": "beautiful",
    "translation": "güzel",
    "definition": "pleasing to the senses or mind aesthetically",
    "part_of_speech": "adjective",
    "level": "A2",
    "example": "It's a beautiful day today."
  }}
]"""

# Fallback prompt for simpler extraction
SIMPLE_VOCABULARY_PROMPT = """Extract the main vocabulary words from this educational text.

Text:
---
{module_text}
---

List {max_words} important vocabulary words for language learners.

Respond with ONLY a valid JSON array:
[
  {{
    "word": "example",
    "translation": "örnek",
    "definition": "a thing serving as a model or illustration",
    "part_of_speech": "noun",
    "level": "A2",
    "example": "This is an example sentence."
  }}
]"""

# Bilingual extraction prompt (for Turkish + English content)
BILINGUAL_VOCABULARY_PROMPT = """Extract vocabulary from this bilingual (English-Turkish) educational text.

For each English vocabulary word, provide:
- The English word
- Its Turkish translation (may already be in the text)
- Definition in English
- Part of speech
- CEFR level
- Example sentence

Text:
---
{module_text}
---

Extract {max_words} vocabulary words. Focus on the English words and their Turkish translations.

Respond with ONLY a valid JSON array:
[
  {{
    "word": "greeting",
    "translation": "selamlama",
    "definition": "a polite word or sign of welcome",
    "part_of_speech": "noun",
    "level": "A1",
    "example": "A friendly greeting makes people feel welcome."
  }}
]"""


def build_vocabulary_extraction_prompt(
    module_text: str,
    difficulty: str = "B1",
    max_words: int = 50,
    max_length: int = 8000,
) -> str:
    """
    Build the vocabulary extraction prompt with the given module text.

    Args:
        module_text: The text content to analyze.
        difficulty: Target CEFR difficulty level.
        max_words: Maximum number of words to extract.
        max_length: Maximum text length to include.

    Returns:
        Formatted prompt string.
    """
    # Truncate text if too long
    if len(module_text) > max_length:
        module_text = module_text[:max_length] + "\n\n[Text truncated...]"

    return VOCABULARY_EXTRACTION_PROMPT.format(
        module_text=module_text,
        difficulty=difficulty,
        max_words=max_words,
    )


def build_simple_vocabulary_prompt(
    module_text: str,
    max_words: int = 30,
    max_length: int = 4000,
) -> str:
    """
    Build a simpler vocabulary extraction prompt for fallback.

    Args:
        module_text: The text content to analyze.
        max_words: Maximum number of words to extract.
        max_length: Maximum text length to include.

    Returns:
        Formatted prompt string.
    """
    if len(module_text) > max_length:
        module_text = module_text[:max_length] + "\n\n[Text truncated...]"

    return SIMPLE_VOCABULARY_PROMPT.format(
        module_text=module_text,
        max_words=max_words,
    )


def build_bilingual_vocabulary_prompt(
    module_text: str,
    max_words: int = 50,
    max_length: int = 8000,
) -> str:
    """
    Build the bilingual vocabulary extraction prompt.

    Args:
        module_text: The text content to analyze.
        max_words: Maximum number of words to extract.
        max_length: Maximum text length to include.

    Returns:
        Formatted prompt string.
    """
    if len(module_text) > max_length:
        module_text = module_text[:max_length] + "\n\n[Text truncated...]"

    return BILINGUAL_VOCABULARY_PROMPT.format(
        module_text=module_text,
        max_words=max_words,
    )
