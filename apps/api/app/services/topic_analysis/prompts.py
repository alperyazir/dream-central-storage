"""LLM prompt templates for topic analysis."""

# System prompt for educational content analysis
SYSTEM_PROMPT = """You are an expert educational content analyzer specializing in language learning materials.
Your task is to analyze educational text and extract structured information about topics, grammar, difficulty, and skills.
Always respond with valid JSON only. Do not include any explanatory text outside the JSON object.
Be precise and consistent with CEFR levels (A1, A2, B1, B2, C1, C2) for difficulty assessment."""

# Combined topic extraction prompt - analyzes all aspects in one call
TOPIC_EXTRACTION_PROMPT = """Analyze this educational content and extract the following information:

1. **Main Topics** (3-5 key topics covered in this content)
2. **Grammar Points** (grammatical structures taught or used, if this is language learning content)
3. **Difficulty Level** (CEFR level: A1/A2/B1/B2/C1/C2 based on vocabulary and sentence complexity)
4. **Language** (primary language of the content: "en" for English, "tr" for Turkish, "bilingual" if mixed)
5. **Target Skills** (which skills this content helps develop: reading, writing, speaking, listening)

Content to analyze:
---
{module_text}
---

Respond with ONLY a valid JSON object in this exact format:
{{
  "topics": ["topic1", "topic2", "topic3"],
  "grammar_points": ["grammar point 1", "grammar point 2"],
  "difficulty": "A1",
  "language": "en",
  "target_skills": ["reading", "listening"]
}}

Guidelines:
- topics: Extract 3-5 main educational topics (e.g., "greetings", "family vocabulary", "present tense")
- grammar_points: List specific grammar structures (e.g., "present simple", "articles", "modal verbs"). Leave empty [] if not a language learning text.
- difficulty: Use CEFR scale. A1=beginner, A2=elementary, B1=intermediate, B2=upper-intermediate, C1=advanced, C2=proficient
- language: "en" for English, "tr" for Turkish, "bilingual" if content mixes both languages significantly
- target_skills: Include only skills that this content clearly develops"""

# Fallback prompt for when combined analysis fails - simpler extraction
SIMPLE_TOPIC_PROMPT = """Extract the main topics from this educational content.

Content:
---
{module_text}
---

Respond with ONLY a valid JSON object:
{{
  "topics": ["topic1", "topic2", "topic3"],
  "difficulty": "B1",
  "language": "en"
}}"""

# Language detection prompt - used as fallback if main analysis doesn't detect language
LANGUAGE_DETECTION_PROMPT = """Identify the primary language of this text.

Text sample:
---
{text_sample}
---

Respond with ONLY a valid JSON object:
{{
  "language": "en",
  "confidence": 0.95,
  "is_bilingual": false,
  "secondary_language": null
}}

Use:
- "en" for English
- "tr" for Turkish
- "bilingual" if the text significantly mixes both languages
- confidence: 0.0 to 1.0
- is_bilingual: true if mixed language content
- secondary_language: the other language if bilingual, null otherwise"""

# Difficulty assessment prompt - used for detailed difficulty analysis
DIFFICULTY_DETECTION_PROMPT = """Assess the difficulty level of this educational content using the CEFR scale.

Content:
---
{module_text}
---

Analyze based on:
1. Vocabulary complexity
2. Sentence structure complexity
3. Grammar patterns used
4. Topic abstraction level

Respond with ONLY a valid JSON object:
{{
  "difficulty": "A2",
  "confidence": 0.85,
  "reasoning": "Uses simple present tense, basic vocabulary, short sentences"
}}

CEFR Levels:
- A1: Beginner - Very basic phrases, simple vocabulary
- A2: Elementary - Simple sentences, everyday topics
- B1: Intermediate - Clear standard input, familiar topics
- B2: Upper-Intermediate - Complex texts, abstract topics
- C1: Advanced - Demanding texts, implicit meaning
- C2: Proficient - Near-native complexity"""

# Grammar extraction prompt - used for detailed grammar analysis
GRAMMAR_EXTRACTION_PROMPT = """Extract grammar points taught or practiced in this language learning content.

Content:
---
{module_text}
---

Respond with ONLY a valid JSON object:
{{
  "grammar_points": [
    "present simple tense",
    "definite articles",
    "question formation"
  ],
  "is_language_learning": true
}}

Focus on:
- Verb tenses (present simple, past continuous, etc.)
- Articles and determiners
- Sentence structures (questions, negatives, conditionals)
- Prepositions and conjunctions
- Modal verbs
- Word order patterns

Set is_language_learning to false if this is not a language learning text."""


def build_topic_extraction_prompt(module_text: str, max_length: int = 8000) -> str:
    """
    Build the topic extraction prompt with the given module text.

    Args:
        module_text: The text content to analyze.
        max_length: Maximum text length to include.

    Returns:
        Formatted prompt string.
    """
    # Truncate text if too long
    if len(module_text) > max_length:
        module_text = module_text[:max_length] + "\n\n[Text truncated...]"

    return TOPIC_EXTRACTION_PROMPT.format(module_text=module_text)


def build_simple_topic_prompt(module_text: str, max_length: int = 4000) -> str:
    """
    Build a simpler topic extraction prompt for fallback.

    Args:
        module_text: The text content to analyze.
        max_length: Maximum text length to include.

    Returns:
        Formatted prompt string.
    """
    if len(module_text) > max_length:
        module_text = module_text[:max_length] + "\n\n[Text truncated...]"

    return SIMPLE_TOPIC_PROMPT.format(module_text=module_text)


def build_language_detection_prompt(text_sample: str, max_length: int = 2000) -> str:
    """
    Build the language detection prompt.

    Args:
        text_sample: Sample text for language detection.
        max_length: Maximum text length to include.

    Returns:
        Formatted prompt string.
    """
    if len(text_sample) > max_length:
        text_sample = text_sample[:max_length]

    return LANGUAGE_DETECTION_PROMPT.format(text_sample=text_sample)


def build_difficulty_detection_prompt(module_text: str, max_length: int = 6000) -> str:
    """
    Build the difficulty detection prompt.

    Args:
        module_text: The text content to analyze.
        max_length: Maximum text length to include.

    Returns:
        Formatted prompt string.
    """
    if len(module_text) > max_length:
        module_text = module_text[:max_length] + "\n\n[Text truncated...]"

    return DIFFICULTY_DETECTION_PROMPT.format(module_text=module_text)


def build_grammar_extraction_prompt(module_text: str, max_length: int = 6000) -> str:
    """
    Build the grammar extraction prompt.

    Args:
        module_text: The text content to analyze.
        max_length: Maximum text length to include.

    Returns:
        Formatted prompt string.
    """
    if len(module_text) > max_length:
        module_text = module_text[:max_length] + "\n\n[Text truncated...]"

    return GRAMMAR_EXTRACTION_PROMPT.format(module_text=module_text)
