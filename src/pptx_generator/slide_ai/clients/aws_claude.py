"""AWS Bedrock Claude クライアント。"""

from __future__ import annotations

import json

from ..constants import APPLICATION_JSON, DEFAULT_MAX_TOKENS
from ..errors import LLMClientConfigurationError
from ..models import AIGenerationRequest, SlideMatchRequest
from ..prompt_builder import build_system_prompt, build_user_prompt
from ..response_parser import build_generation_response, build_slide_match_response
from ...llm import load_aws_claude_config


class AwsClaudeClient:
    """AWS Bedrock Claude クライアント。"""

    def __init__(
        self,
        runtime_client,
        *,
        model_id: str,
        max_tokens: int,
        inference_profile_arn: str | None,
        temperature: float,
    ) -> None:
        self._client = runtime_client
        self._model_id = model_id
        self._max_tokens = max_tokens
        self._inference_profile_arn = inference_profile_arn
        self._temperature = temperature

    def _resolve_model_id(self, override: str | None) -> str:
        model_id = override if override and override.strip() else self._model_id
        return self._model_id if model_id == "mock-local" else model_id

    def _invoke_bedrock(self, *, model_id: str, payload: dict[str, object]) -> str:
        invoke_kwargs = {
            "modelId": model_id,
            "body": json.dumps(payload),
            "contentType": APPLICATION_JSON,
            "accept": APPLICATION_JSON,
        }
        if self._inference_profile_arn:
            invoke_kwargs["inferenceProfileArn"] = self._inference_profile_arn

        response = self._client.invoke_model(**invoke_kwargs)
        body = response.get("body")
        if hasattr(body, "read"):
            body_text = body.read()
        else:  # pragma: no cover - unexpected response type
            body_text = body
        if isinstance(body_text, (bytes, bytearray)):
            body_text = body_text.decode("utf-8")
        data = json.loads(body_text)
        contents = data.get("content", [])
        text_parts = [item.get("text", "") for item in contents if isinstance(item, dict)]
        return "\n".join(text_parts)

    @classmethod
    def from_env(cls) -> "AwsClaudeClient":
        import boto3
        from botocore.exceptions import NoCredentialsError

        config = load_aws_claude_config(
            default_model_id="anthropic.claude-3-haiku-20240307-v1:0",
            default_temperature=0.3,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=LLMClientConfigurationError,
        )

        session_kwargs: dict[str, object] = {}
        if config.profile:
            session_kwargs["profile_name"] = config.profile
        if config.region:
            session_kwargs["region_name"] = config.region
        session = boto3.Session(**session_kwargs)
        credentials = session.get_credentials()
        if credentials is None:
            raise LLMClientConfigurationError(
                "AWS 認証情報が見つかりません。AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY を設定するか、`aws configure` で設定してください。"
            )

        client_kwargs: dict[str, object] = {}
        if config.region:
            client_kwargs["region_name"] = config.region
        try:
            runtime_client = session.client("bedrock-runtime", **client_kwargs)
        except NoCredentialsError as exc:
            raise LLMClientConfigurationError(
                "AWS 認証情報を利用できません。環境変数または共有クレデンシャルで設定してください。"
            ) from exc
        return cls(
            runtime_client,
            model_id=config.model_id,
            max_tokens=config.max_tokens,
            inference_profile_arn=config.inference_profile_arn,
            temperature=config.temperature,
        )

    def generate(self, request: AIGenerationRequest):
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "system": build_system_prompt(request),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": build_user_prompt(request),
                        }
                    ],
                }
            ],
        }
        model_id = self._resolve_model_id(request.policy.model)

        try:
            text = self._invoke_bedrock(model_id=model_id, payload=payload)
        except Exception as exc:  # pragma: no cover - AWS runtime errors
            from botocore.exceptions import NoCredentialsError

            if isinstance(exc, NoCredentialsError):
                raise LLMClientConfigurationError(
                    "AWS 認証情報を利用できません。AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY を設定してください。"
                ) from exc
            raise
        return build_generation_response(text, request, model=model_id)

    def match_slide(self, request: SlideMatchRequest):
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "system": request.system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": request.prompt,
                        }
                    ],
                }
            ],
        }
        model_id = self._resolve_model_id(request.model)

        response_text = self._invoke_bedrock(model_id=model_id, payload=payload)
        return build_slide_match_response(response_text, request, model=model_id)


__all__ = ["AwsClaudeClient"]
