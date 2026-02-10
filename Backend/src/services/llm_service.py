"""LLM Service - Processamento de texto com Gemini 2.5 Flash."""

import json
import os
from typing import AsyncIterator, Dict, Any, List, Callable, Awaitable, Optional

import structlog
from google import genai
from google.genai import types

from src.config import settings

logger = structlog.get_logger(__name__)


class LLMService:
    """
    LLM baseado em texto usando Gemini 2.5 Flash.
    Suporta respostas streaming e function calling.
    """

    def __init__(self):
        self.client: Optional[genai.Client] = None
        self.model = settings.gemini_llm_model

    async def initialize(self):
        """Inicializa o cliente Gemini com Vertex AI."""
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
            settings.google_application_credentials
        )
        self.client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_region,
        )
        logger.info("LLM Service inicializado", model=self.model)

    async def generate_response(
        self,
        user_text: str,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        tool_declarations: List[types.FunctionDeclaration],
        execute_tool: Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]],
    ) -> AsyncIterator[str]:
        """
        Gera resposta de texto em streaming.

        Emite chunks de texto a medida que sao gerados.
        Gere tool calls internamente, executando-as via callback e continuando a geracao.

        Args:
            user_text: Texto transcrito do utilizador
            system_prompt: System prompt completo
            conversation_history: Lista de {"role": "user"|"model", "text": "..."}
            tool_declarations: Declaracoes de funcoes para tools
            execute_tool: Callback async para executar uma tool

        Yields:
            Chunks de texto da resposta
        """
        if not self.client:
            raise RuntimeError("LLM Service nao inicializado")

        # Construir contents a partir do historico + nova mensagem
        contents = []
        for turn in conversation_history:
            role = turn["role"]  # "user" ou "model"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=turn["text"])])
            )

        # Adicionar mensagem atual do utilizador
        contents.append(
            types.Content(role="user", parts=[types.Part(text=user_text)])
        )

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=settings.gemini_temperature,
            tools=[types.Tool(function_declarations=tool_declarations)],
        )

        # Streaming para TTS progressivo frase-a-frase
        async for text_chunk in self._stream_with_tool_handling(
            contents, config, execute_tool
        ):
            yield text_chunk

    async def _stream_with_tool_handling(
        self,
        contents: list,
        config: types.GenerateContentConfig,
        execute_tool: Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]],
    ) -> AsyncIterator[str]:
        """Stream com tratamento de tool calls (pode ter multiplas rondas)."""
        max_tool_rounds = 5  # Limite para evitar loops infinitos

        for _ in range(max_tool_rounds):
            had_tool_call = False
            # Acumular TODAS as parts do modelo (texto + function_call)
            # para que o follow-up apos tool call inclua o texto ja gerado.
            # Sem isto, o modelo nao sabe que ja respondeu e duplica a resposta.
            accumulated_parts = []

            response_stream = await self.client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=config,
            )

            async for chunk in response_stream:
                if not chunk.candidates or not chunk.candidates[0].content.parts:
                    continue

                for part in chunk.candidates[0].content.parts:
                    # Verificar function call
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        tool_name = fc.name

                        # Converter args para dict
                        if hasattr(fc.args, "_pb"):
                            from google.protobuf.json_format import MessageToDict

                            tool_args = MessageToDict(fc.args._pb)
                        elif isinstance(fc.args, dict):
                            tool_args = fc.args
                        else:
                            tool_args = dict(fc.args) if fc.args else {}

                        logger.info(
                            "LLM tool call",
                            tool_name=tool_name,
                            args=json.dumps(tool_args, ensure_ascii=False)[:100],
                        )

                        # Executar a tool
                        tool_result = await execute_tool(tool_name, tool_args)

                        # Incluir texto acumulado + function_call no follow-up
                        # para o modelo saber o que ja disse antes da tool call
                        accumulated_parts.append(part)
                        contents.append(
                            types.Content(
                                role="model", parts=accumulated_parts
                            )
                        )
                        contents.append(
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part(
                                        function_response=types.FunctionResponse(
                                            name=tool_name,
                                            response=tool_result,
                                        )
                                    )
                                ],
                            )
                        )

                        had_tool_call = True
                        break  # Sair do loop de parts para re-gerar

                    # Texto normal — yield para TTS e acumular para contexto
                    elif hasattr(part, "text") and part.text:
                        accumulated_parts.append(part)
                        yield part.text

                if had_tool_call:
                    break  # Sair do loop de chunks para re-gerar

            if not had_tool_call:
                # Resposta completa sem mais tool calls
                return

        logger.warning("LLM atingiu limite maximo de rondas de tool calls")
