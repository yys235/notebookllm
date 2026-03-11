"""User settings API routes."""
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.dependencies import CurrentUser, DBSession
from app.models.user_settings import UserSettings

router = APIRouter()


# Request/Response Models
class AISettings(BaseModel):
    provider: str | None = None
    apiKey: str | None = None
    baseUrl: str | None = None
    model: str | None = None
    temperature: float | None = None
    maxTokens: int | None = None
    enableRag: bool | None = None


class EmbeddingSettings(BaseModel):
    provider: str | None = None
    apiKey: str | None = None
    baseUrl: str | None = None
    model: str | None = None


class AppearanceSettings(BaseModel):
    theme: str | None = None
    fontSize: str | None = None
    editorMode: str | None = None


class UserSettingsUpdate(BaseModel):
    ai: AISettings | None = None
    embedding: EmbeddingSettings | None = None
    appearance: AppearanceSettings | None = None


class AISettingsResponse(BaseModel):
    provider: str = "ollama"
    apiKey: str | None = None
    baseUrl: str = "http://192.168.123.220:11434"
    model: str | None = None
    temperature: float = 0.7
    maxTokens: int = 2000
    enableRag: bool = True


class EmbeddingSettingsResponse(BaseModel):
    provider: str = "ollama"
    apiKey: str | None = None
    baseUrl: str = "http://192.168.123.220:11434"
    model: str | None = None


class AppearanceSettingsResponse(BaseModel):
    theme: str = "light"
    fontSize: str = "medium"
    editorMode: str = "rich"


class UserSettingsResponse(BaseModel):
    ai: AISettingsResponse
    embedding: EmbeddingSettingsResponse
    appearance: AppearanceSettingsResponse


def model_to_response(settings: UserSettings) -> UserSettingsResponse:
    """Convert model to response."""
    return UserSettingsResponse(
        ai=AISettingsResponse(
            provider=settings.ai_provider or "ollama",
            apiKey=settings.ai_api_key,
            baseUrl=settings.ai_base_url or "http://192.168.123.220:11434",
            model=settings.ai_model,
            temperature=float(settings.ai_temperature) if settings.ai_temperature else 0.7,
            maxTokens=int(settings.ai_max_tokens) if settings.ai_max_tokens else 2000,
            enableRag=(settings.ai_enable_rag == "true"),
        ),
        embedding=EmbeddingSettingsResponse(
            provider=settings.embedding_provider or "ollama",
            apiKey=settings.embedding_api_key,
            baseUrl=settings.embedding_base_url or "http://192.168.123.220:11434",
            model=settings.embedding_model,
        ),
        appearance=AppearanceSettingsResponse(
            theme=settings.theme or "light",
            fontSize=settings.font_size or "medium",
            editorMode=settings.editor_mode or "rich",
        ),
    )


@router.get("")
async def get_settings(current_user: CurrentUser, db: DBSession):
    """Get current user's settings."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        # Return empty settings if user has never configured
        return None

    return model_to_response(settings)


@router.put("", response_model=UserSettingsResponse)
async def update_settings(
    data: UserSettingsUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Update user settings."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    # Update AI settings - only update fields that are provided
    if data.ai:
        if data.ai.provider is not None:
            settings.ai_provider = data.ai.provider
        if data.ai.apiKey is not None:
            settings.ai_api_key = data.ai.apiKey
        if data.ai.baseUrl is not None:
            settings.ai_base_url = data.ai.baseUrl
        if data.ai.model is not None:
            settings.ai_model = data.ai.model
        if data.ai.temperature is not None:
            settings.ai_temperature = str(data.ai.temperature)
        if data.ai.maxTokens is not None:
            settings.ai_max_tokens = str(data.ai.maxTokens)
        if data.ai.enableRag is not None:
            settings.ai_enable_rag = "true" if data.ai.enableRag else "false"

    # Update Embedding settings - only update fields that are provided
    if data.embedding:
        if data.embedding.provider is not None:
            settings.embedding_provider = data.embedding.provider
        if data.embedding.apiKey is not None:
            settings.embedding_api_key = data.embedding.apiKey
        if data.embedding.baseUrl is not None:
            settings.embedding_base_url = data.embedding.baseUrl
        if data.embedding.model is not None:
            settings.embedding_model = data.embedding.model

    # Update Appearance settings - only update fields that are provided
    if data.appearance:
        if data.appearance.theme is not None:
            settings.theme = data.appearance.theme
        if data.appearance.fontSize is not None:
            settings.font_size = data.appearance.fontSize
        if data.appearance.editorMode is not None:
            settings.editor_mode = data.appearance.editorMode

    await db.commit()
    await db.refresh(settings)

    return model_to_response(settings)
