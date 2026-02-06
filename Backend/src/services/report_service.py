"""Report Service - Geracao de relatorio pos-sessao com Gemini 2.0 Flash."""

import json
import os
from typing import List, Dict, Any, Optional

import structlog
from google import genai
from google.genai import types

from src.config import settings

logger = structlog.get_logger(__name__)


REPORT_PROMPT = """Analisa a seguinte conversa entre a EmpatIA (agente de companhia para idosos) e um utilizador.

Gera um relatorio de bem-estar estruturado com as seguintes seccoes:

## Resumo da Sessao
- Duracao aproximada
- Topicos abordados
- Fluxo geral da conversa

## Estado Emocional Observado
- Tom emocional predominante (alegre, neutro, triste, ansioso, etc.)
- Mudancas de humor durante a conversa
- Sinais de alerta (se existirem)

## Topicos-Chave
- Lista dos principais assuntos discutidos
- Informacoes novas relevantes mencionadas pelo utilizador

## Informacoes de Saude Mencionadas
- Queixas fisicas ou de saude
- Medicamentos mencionados
- Alteracoes de mobilidade ou autonomia

## Interacoes Sociais
- Referencias a familia, amigos, vizinhos
- Sinais de isolamento ou solidao
- Atividades sociais mencionadas

## Recomendacoes
- Sugestoes para a proxima sessao
- Pontos de atencao para cuidadores
- Topicos a revisitar

Responde em Portugues de Portugal (PT-PT). Se objetivo e clinico mas empatico.

CONVERSA:
{transcript}
"""

EXTRACTION_PROMPT = """Do seguinte relatorio, extrai em formato JSON:
{{"summary": "resumo em 1-2 frases", "emotional_tone": "tom predominante", "key_topics": ["topico1", "topico2"]}}

Relatorio:
{report_text}
"""


class ReportService:
    """Geracao de relatorio pos-sessao usando Gemini 2.0 Flash."""

    def __init__(self):
        self.client: Optional[genai.Client] = None
        self.model = settings.gemini_report_model

    async def initialize(self):
        """Inicializa o cliente Gemini."""
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
            settings.google_application_credentials
        )
        self.client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_region,
        )
        logger.info("Report Service inicializado", model=self.model)

    async def generate_report(
        self, conversation_turns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Gera relatorio de bem-estar a partir da transcricao da conversa.

        Args:
            conversation_turns: Lista de {"speaker": "user"|"assistant", "text": "...", "timestamp": ...}

        Returns:
            Dict com "report_text", "summary", "emotional_tone", "key_topics"
        """
        if not self.client:
            raise RuntimeError("Report Service nao inicializado")

        if not conversation_turns:
            return {
                "report_text": "",
                "summary": "Sessao sem conversa registada.",
                "emotional_tone": "neutro",
                "key_topics": [],
            }

        # Formatar transcricao
        transcript_lines = []
        for turn in conversation_turns:
            speaker = "Utilizador" if turn["speaker"] == "user" else "EmpatIA"
            transcript_lines.append(f"{speaker}: {turn['text']}")
        transcript = "\n".join(transcript_lines)

        # Limitar transcricao para evitar exceder context window
        if len(transcript) > 50000:
            transcript = transcript[-50000:]

        try:
            # 1. Gerar relatorio completo
            prompt = REPORT_PROMPT.format(transcript=transcript)

            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                ),
            )

            report_text = response.text if response.text else ""

            # 2. Extrair metadados estruturados via JSON mode
            extraction_prompt = EXTRACTION_PROMPT.format(report_text=report_text)

            extraction = await self.client.aio.models.generate_content(
                model=self.model,
                contents=extraction_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            try:
                extracted = json.loads(extraction.text)
            except (json.JSONDecodeError, TypeError):
                extracted = {
                    "summary": (
                        transcript_lines[0]
                        if transcript_lines
                        else "Conversa com EmpatIA"
                    ),
                    "emotional_tone": "neutro",
                    "key_topics": [],
                }

            logger.info(
                "Relatorio gerado",
                summary=extracted.get("summary", "")[:80],
                emotional_tone=extracted.get("emotional_tone", ""),
                topics_count=len(extracted.get("key_topics", [])),
            )

            return {
                "report_text": report_text,
                "summary": extracted.get("summary", ""),
                "emotional_tone": extracted.get("emotional_tone", "neutro"),
                "key_topics": extracted.get("key_topics", []),
            }

        except Exception as e:
            logger.error("Geracao de relatorio falhou", error=str(e), exc_info=True)
            return {
                "report_text": "",
                "summary": "Erro ao gerar relatorio.",
                "emotional_tone": "neutro",
                "key_topics": [],
            }
