"""Tool para gestão de memórias do utilizador."""

from typing import Optional, Literal
from pydantic import BaseModel, Field
import structlog

from src.database import MemoryStore
from src.database.memory_store import MemoryAction, MemoryCategory

logger = structlog.get_logger(__name__)


class ManageMemoryInput(BaseModel):
    """Input schema para a tool manage_memory."""

    action: Literal["ADD", "UPDATE", "DELETE", "SEARCH"] = Field(
        ...,
        description="Ação: ADD, UPDATE, DELETE, SEARCH",
    )
    category: Literal["familia", "saude", "hobbies", "interesses", "geral"] = Field(
        ...,
        description="Categoria: familia, saude, hobbies, interesses, geral",
    )
    entity_type: str = Field(
        ...,
        description="Tipo de entidade (ex: filho, neto, doenca, hobby)",
    )
    entity_name: Optional[str] = Field(
        None,
        description="Nome específico da entidade",
    )
    content: Optional[str] = Field(
        None,
        description="Conteúdo da memória",
    )
    importance: Optional[int] = Field(
        5,
        ge=1,
        le=10,
        description="Importância 1-10",
    )
    memory_id: Optional[int] = Field(
        None,
        description="ID da memória para UPDATE/DELETE",
    )
    search_query: Optional[str] = Field(
        None,
        description="Query para SEARCH",
    )


class MemoryTool:
    """Tool de gestão de memórias."""

    def __init__(self):
        self.store = MemoryStore()

    async def execute(self, params: ManageMemoryInput, user_id: str) -> dict:
        """Executa operação sobre memória."""
        try:
            if params.action == "ADD":
                if not params.content:
                    return {"success": False, "error": "Conteúdo obrigatório"}

                memory = await self.store.add_memory(
                    user_id=user_id,
                    category=params.category,
                    entity_type=params.entity_type,
                    entity_name=params.entity_name,
                    content=params.content,
                    importance=params.importance or 5,
                )

                return {
                    "success": True,
                    "action": "ADD",
                    "memory_id": memory.id,
                    "message": f"Memória adicionada: {params.entity_type}",
                }

            elif params.action == "UPDATE":
                if not params.memory_id:
                    return {"success": False, "error": "memory_id obrigatório"}

                memory = await self.store.update_memory(
                    memory_id=params.memory_id,
                    content=params.content,
                    importance=params.importance,
                )

                return {
                    "success": bool(memory),
                    "action": "UPDATE",
                    "memory_id": params.memory_id,
                }

            elif params.action == "DELETE":
                if not params.memory_id:
                    return {"success": False, "error": "memory_id obrigatório"}

                deleted = await self.store.delete_memory(params.memory_id)
                return {"success": deleted, "action": "DELETE"}

            elif params.action == "SEARCH":
                if not params.search_query:
                    return {"success": False, "error": "search_query obrigatório"}

                memories = await self.store.search_memories(
                    user_id=user_id,
                    query=params.search_query,
                    category=params.category if params.category != "geral" else None,
                )

                return {
                    "success": True,
                    "action": "SEARCH",
                    "results": [
                        {
                            "id": m.id,
                            "content": m.content,
                            "similarity": round(m.similarity_score or 0, 3),
                        }
                        for m in memories
                    ],
                }

            return {"success": False, "error": f"Ação desconhecida: {params.action}"}

        except Exception as e:
            logger.error("Erro manage_memory", error=str(e))
            return {"success": False, "error": str(e)}


memory_tool = MemoryTool()


async def manage_memory_tool(params: ManageMemoryInput, user_id: str) -> dict:
    """Wrapper para tool."""
    return await memory_tool.execute(params, user_id)


# Definição da tool para o Google ADK
MANAGE_MEMORY_TOOL_DEFINITION = {
    "name": "manage_memory",
    "description": """Gestão silenciosa da memória do utilizador. USA ESTA TOOL FREQUENTEMENTE.

**IMPORTANTE:** Esta tool é SILENCIOSA. NUNCA menciones ao utilizador que estás a usar.

**Quando usar:**
- Sempre que o utilizador menciona família, amigos, saúde, hobbies
- Quando corriges ou atualizas informação anterior
- Quando removes informação desatualizada ou contradita
- Para pesquisar contexto relevante antes de responder

**Ações:**
- ADD: Guardar nova informação
- UPDATE: Corrigir/atualizar informação existente (precisa do memory_id)
- DELETE: Remover informação desatualizada (precisa do memory_id)
- SEARCH: Pesquisar memórias relevantes

**Categorias:**
- familia: Cônjuges, filhos, netos, irmãos, pais, família alargada
- saude: Doenças, medicamentos, consultas médicas, mobilidade, alergias
- hobbies: Atividades de lazer, passatempos, desportos
- interesses: Tópicos de interesse (política, culinária, jardinagem, etc.)
- geral: Outras informações relevantes

**Importância (1-10):**
- 9-10: Informação crítica (saúde grave, família próxima)
- 6-8: Informação importante (hobbies regulares, condições de saúde)
- 3-5: Informação moderada (preferências, interesses casuais)
- 1-2: Informação trivial

NUNCA digas: "Vou guardar essa informação" ou "Guardei na memória".""",
    "parameters": ManageMemoryInput.model_json_schema(),
}
