"""Topic analysis service for AI book processing pipeline."""

from app.services.topic_analysis.models import (
    BookAnalysisResult,
    CEFRLevel,
    DetectedLanguage,
    InvalidLLMResponseError,
    LLMAnalysisError,
    ModuleAnalysisResult,
    NoModulesFoundError,
    TargetSkill,
    TopicAnalysisError,
    TopicResult,
)
from app.services.topic_analysis.prompts import (
    SYSTEM_PROMPT,
    TOPIC_EXTRACTION_PROMPT,
    build_topic_extraction_prompt,
)
from app.services.topic_analysis.service import (
    TopicAnalysisService,
    get_topic_analysis_service,
)
from app.services.topic_analysis.storage import (
    TopicStorage,
    get_topic_storage,
)

__all__ = [
    # Service
    "TopicAnalysisService",
    "get_topic_analysis_service",
    # Storage
    "TopicStorage",
    "get_topic_storage",
    # Data models
    "TopicResult",
    "ModuleAnalysisResult",
    "BookAnalysisResult",
    # Enums
    "CEFRLevel",
    "TargetSkill",
    "DetectedLanguage",
    # Exceptions
    "TopicAnalysisError",
    "LLMAnalysisError",
    "NoModulesFoundError",
    "InvalidLLMResponseError",
    # Prompts
    "SYSTEM_PROMPT",
    "TOPIC_EXTRACTION_PROMPT",
    "build_topic_extraction_prompt",
]
