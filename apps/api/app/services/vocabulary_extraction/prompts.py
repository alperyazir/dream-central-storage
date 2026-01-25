"""LLM prompt templates for vocabulary extraction."""

# System prompt for vocabulary extraction
SYSTEM_PROMPT = """You are a vocabulary extraction API that returns JSON only.
Extract vocabulary words from educational text with definitions and translations.
CRITICAL: Return ONLY a raw JSON array. No markdown. No code blocks. No explanation. No text before or after the JSON."""

# Main vocabulary extraction prompt
VOCABULARY_EXTRACTION_PROMPT = """Extract {max_words} vocabulary words from this {difficulty}-level educational module.

MODULE TITLE: {module_title}

TEXT:
{module_text}

IMPORTANT: Focus on words that are KEY to learning the module's topic "{module_title}".
- Extract words that students need to learn for this specific topic
- Prioritize nouns, verbs, and adjectives directly related to the theme
- Skip words that are not essential to understanding the topic
- Use infinitive for verbs, singular for nouns

Return a JSON array with these fields for each word:
- word: base form
- translation: Turkish translation
- definition: simple English definition
- part_of_speech: noun/verb/adjective/adverb
- level: A1/A2/B1/B2/C1/C2
- example: example sentence

OUTPUT FORMAT - Return ONLY this JSON array, nothing else:
[{{"word":"elephant","translation":"fil","definition":"a large animal with a trunk","part_of_speech":"noun","level":"A1","example":"The elephant is big."}}]"""

# Fallback prompt for simpler extraction
SIMPLE_VOCABULARY_PROMPT = """Extract {max_words} vocabulary words about "{module_title}" from this text. Return ONLY a JSON array.
Focus on words essential to the topic. Skip unrelated common words.

TEXT:
{module_text}

OUTPUT (JSON array only, no other text):
[{{"word":"cat","translation":"kedi","definition":"a small pet animal","part_of_speech":"noun","level":"A1","example":"I have a cat."}}]"""

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
    module_title: str = "",
    difficulty: str = "B1",
    max_words: int = 50,
    max_length: int = 8000,
) -> str:
    """
    Build the vocabulary extraction prompt with the given module text.

    Args:
        module_text: The text content to analyze.
        module_title: Title of the module for topic context.
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
        module_title=module_title or "Unknown",
        difficulty=difficulty,
        max_words=max_words,
    )


def build_simple_vocabulary_prompt(
    module_text: str,
    module_title: str = "",
    max_words: int = 30,
    max_length: int = 4000,
) -> str:
    """
    Build a simpler vocabulary extraction prompt for fallback.

    Args:
        module_text: The text content to analyze.
        module_title: Title of the module for topic context.
        max_words: Maximum number of words to extract.
        max_length: Maximum text length to include.

    Returns:
        Formatted prompt string.
    """
    if len(module_text) > max_length:
        module_text = module_text[:max_length] + "\n\n[Text truncated...]"

    return SIMPLE_VOCABULARY_PROMPT.format(
        module_text=module_text,
        module_title=module_title or "this topic",
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
