"""Tool para pesquisa Google (ancoragem em factos atuais)."""

import os
from typing import Optional
from pydantic import BaseModel, Field
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


class GoogleSearchInput(BaseModel):
    """Input schema para a tool google_search."""

    query: str = Field(
        ...,
        description="Query de pesquisa (ex: 'Notícias de hoje em Portugal', 'Tempo em Lisboa')",
    )
    num_results: Optional[int] = Field(
        5,
        ge=1,
        le=10,
        description="Número de resultados a retornar (1-10)",
    )


async def google_search_tool(params: GoogleSearchInput) -> dict:
    """
    Ferramenta para pesquisa Google - ancoragem em factos atuais.

    Use para:
    - Validar factos históricos portugueses
    - Obter notícias atuais de Portugal
    - Verificar condições meteorológicas
    - Confirmar informações sobre eventos, tradições, etc.

    Esta ferramenta usa a API de Grounding do Google Gemini para obter
    informações atualizadas da web.
    """
    try:
        # Usar o Google Search via Gemini Grounding (Vertex AI)
        from google import genai

        # Configurar credenciais Vertex AI
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_application_credentials

        client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_region,
        )

        # Fazer uma chamada ao Gemini com grounding habilitado
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"""Pesquisa as seguintes informações atualizadas e responde em Português de Portugal (PT-PT):

Query: {params.query}

Fornece informações factuais e atualizadas. Se for sobre meteorologia, inclui a previsão.
Se for sobre notícias, menciona as mais recentes e relevantes.
Responde de forma concisa e objetiva.""",
            config={
                "tools": [{"google_search": {}}],
                "temperature": 0.3,
            },
        )

        # Extrair texto da resposta
        result_text = ""
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text"):
                    result_text += part.text

        # Extrair fontes se disponíveis
        sources = []
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "grounding_metadata") and candidate.grounding_metadata:
                grounding = candidate.grounding_metadata
                if hasattr(grounding, "grounding_chunks"):
                    for chunk in grounding.grounding_chunks[:params.num_results]:
                        if hasattr(chunk, "web") and chunk.web:
                            sources.append({
                                "title": getattr(chunk.web, "title", ""),
                                "uri": getattr(chunk.web, "uri", ""),
                            })

        logger.info(
            "Pesquisa Google concluída",
            query=params.query,
            sources_count=len(sources),
        )

        return {
            "success": True,
            "query": params.query,
            "result": result_text,
            "sources": sources,
        }

    except Exception as e:
        logger.error("Erro na pesquisa Google", error=str(e), query=params.query)

        return {
            "success": False,
            "query": params.query,
            "error": f"Não foi possível completar a pesquisa: {str(e)}",
            "result": None,
            "sources": [],
        }


# Definição da tool para o Google ADK
GOOGLE_SEARCH_TOOL_DEFINITION = {
    "name": "google_search",
    "description": """Pesquisa Google para obter informações atualizadas.

Use para:
- Notícias atuais de Portugal: "Notícias de hoje em Portugal"
- Meteorologia: "Tempo em Lisboa hoje"
- Factos históricos: "História do 25 de Abril"
- Eventos e tradições: "Festas populares em Portugal"
- Verificação de factos mencionados na conversa

IMPORTANTE: Use para ancorar a conversa em factos reais e atuais.
Útil para manter proatividade quando o utilizador está silencioso.""",
    "parameters": GoogleSearchInput.model_json_schema(),
}
