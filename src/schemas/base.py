"""Base schemas and mixins for all Pydantic models.

Provides common configuration and utilities for schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base schema with common configuration.
    
    All schemas should inherit from this class for consistent behavior.
    """
    
    model_config = ConfigDict(
        # Allow population by field name or alias
        populate_by_name=True,
        # Validate on assignment
        validate_assignment=True,
        # Use enum values in serialization
        use_enum_values=True,
        # Allow arbitrary types like Decimal
        arbitrary_types_allowed=True,
        # Serialize Decimal as float in JSON
        json_encoders={
            Decimal: lambda v: float(v) if v is not None else None,
            datetime: lambda v: v.isoformat() if v is not None else None,
        },
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        return self.model_dump(mode="json")


class TimestampMixin(BaseModel):
    """Mixin for models with timestamp."""
    
    timestamp: datetime = Field(default_factory=datetime.now)


class BilingualMixin(BaseModel):
    """Mixin for bilingual (EN/RU) fields."""
    
    def get_localized(self, field: str, lang: str = "en") -> str:
        """Get localized field value.
        
        Args:
            field: Base field name (e.g., 'name')
            lang: Language code ('en' or 'ru')
            
        Returns:
            Localized value, falls back to English if Russian not found.
        """
        if lang == "ru":
            ru_field = f"{field}_ru"
            if hasattr(self, ru_field):
                return getattr(self, ru_field)
        return getattr(self, field, "")
