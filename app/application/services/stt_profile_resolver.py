"""Resolves STT model profiles and merges config."""

from app.domain.entities.model_profile import ModelProfile
from app.application.services.model_resolver import ModelResolver


class STTProfileResolver:
    """STT専用ProfileResolver。voice解決なし。

    設定の優先順位 (後勝ち):
    1. request_options   (最優先: APIリクエストからの指定)
    2. model.provider_config  (Provider固有設定)
    3. model.defaults    (モデル既定値)
    """

    def __init__(self, model_resolver: ModelResolver) -> None:
        self._model_resolver = model_resolver

    def resolve(
        self,
        model_id: str,
        request_options: dict | None = None,
    ) -> tuple[ModelProfile, dict]:
        model = self._model_resolver.get_model(model_id, direction="stt")
        config: dict = {}
        config.update(model.defaults.model_dump())
        config.update(model.provider_config)
        if request_options:
            config.update(request_options)
        return model, config
