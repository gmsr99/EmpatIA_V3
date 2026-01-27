"""Memory Store - Gestão de memórias do utilizador com pgvector."""

import os
import json
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

import structlog
from google import genai

from .connection import DatabaseConnection
from src.config import settings

logger = structlog.get_logger(__name__)


class MemoryCategory(str, Enum):
    """Categorias de memória do utilizador."""

    FAMILIA = "familia"
    SAUDE = "saude"
    HOBBIES = "hobbies"
    INTERESSES = "interesses"
    GERAL = "geral"


class MemoryAction(str, Enum):
    """Ações possíveis sobre memórias."""

    ADD = "ADD"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SEARCH = "SEARCH"


@dataclass
class Memory:
    """Representa uma memória do utilizador."""

    id: Optional[int] = None
    user_id: str = ""
    category: str = ""
    entity_type: str = ""
    entity_name: Optional[str] = None
    content: str = ""
    importance: int = 5
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True
    similarity_score: Optional[float] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MemoryStore:
    """Gestor de memórias do utilizador com suporte a busca semântica."""

    def __init__(self):
        self._embedding_model = "text-embedding-004"
        self._client = None

    async def _get_client(self):
        """Obtém o cliente Gemini para embeddings (Vertex AI)."""
        if self._client is None:
            # Configurar credenciais Vertex AI
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_application_credentials

            self._client = genai.Client(
                vertexai=True,
                project=settings.google_cloud_project,
                location=settings.google_cloud_region,
            )
        return self._client

    async def _generate_embedding(self, text: str) -> List[float]:
        """Gera embedding para um texto usando Gemini."""
        try:
            client = await self._get_client()
            result = await client.aio.models.embed_content(
                model=self._embedding_model,
                contents=text,
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error("Erro ao gerar embedding", error=str(e))
            return [0.0] * 768

    async def ensure_user_exists(self, user_id: str, name: Optional[str] = None) -> None:
        """Garante que o perfil do utilizador existe."""
        existing = await DatabaseConnection.fetchrow(
            "SELECT id FROM user_profiles WHERE user_id = $1", user_id
        )
        if not existing:
            await DatabaseConnection.execute(
                """
                INSERT INTO user_profiles (user_id, name)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO NOTHING
                """,
                user_id,
                name,
            )
            logger.info("Perfil de utilizador criado", user_id=user_id)

    async def add_memory(
        self,
        user_id: str,
        category: str,
        entity_type: str,
        content: str,
        entity_name: Optional[str] = None,
        importance: int = 5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """Adiciona uma nova memória."""
        await self.ensure_user_exists(user_id)

        # Verificar se já existe uma memória similar (para evitar duplicados)
        existing = await self._find_similar_memory(user_id, category, entity_type, entity_name)
        if existing:
            logger.info(
                "Memória similar encontrada, a atualizar",
                memory_id=existing.id,
                entity_name=entity_name,
            )
            return await self.update_memory(
                memory_id=existing.id,
                content=content,
                importance=importance,
                metadata=metadata,
            )

        # Gerar embedding para busca semântica
        embedding_text = f"{category} {entity_type} {entity_name or ''} {content}"
        embedding = await self._generate_embedding(embedding_text)

        # Converter embedding para string PostgreSQL
        embedding_str = f"[{','.join(map(str, embedding))}]"

        row = await DatabaseConnection.fetchrow(
            """
            INSERT INTO user_memories
            (user_id, category, entity_type, entity_name, content, importance, embedding, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7::vector, $8)
            RETURNING id, created_at, updated_at
            """,
            user_id,
            category,
            entity_type,
            entity_name,
            content,
            importance,
            embedding_str,
            json.dumps(metadata or {}),
        )

        logger.info(
            "Memória adicionada",
            memory_id=row["id"],
            category=category,
            entity_type=entity_type,
        )

        return Memory(
            id=row["id"],
            user_id=user_id,
            category=category,
            entity_type=entity_type,
            entity_name=entity_name,
            content=content,
            importance=importance,
            metadata=metadata or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def _find_similar_memory(
        self,
        user_id: str,
        category: str,
        entity_type: str,
        entity_name: Optional[str],
    ) -> Optional[Memory]:
        """Encontra memória similar existente."""
        if entity_name:
            row = await DatabaseConnection.fetchrow(
                """
                SELECT id, content, importance, metadata, created_at, updated_at
                FROM user_memories
                WHERE user_id = $1
                  AND category = $2
                  AND entity_type = $3
                  AND entity_name = $4
                  AND is_active = TRUE
                """,
                user_id,
                category,
                entity_type,
                entity_name,
            )
        else:
            row = await DatabaseConnection.fetchrow(
                """
                SELECT id, content, importance, metadata, created_at, updated_at
                FROM user_memories
                WHERE user_id = $1
                  AND category = $2
                  AND entity_type = $3
                  AND entity_name IS NULL
                  AND is_active = TRUE
                """,
                user_id,
                category,
                entity_type,
            )

        if row:
            return Memory(
                id=row["id"],
                user_id=user_id,
                category=category,
                entity_type=entity_type,
                entity_name=entity_name,
                content=row["content"],
                importance=row["importance"],
                metadata=dict(row["metadata"]) if row["metadata"] else {},
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        return None

    async def update_memory(
        self,
        memory_id: int,
        content: Optional[str] = None,
        importance: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Memory]:
        """Atualiza uma memória existente."""
        updates = []
        params = []
        param_count = 1

        if content is not None:
            updates.append(f"content = ${param_count}")
            params.append(content)
            param_count += 1

            # Atualizar embedding
            row = await DatabaseConnection.fetchrow(
                "SELECT category, entity_type, entity_name FROM user_memories WHERE id = $1",
                memory_id,
            )
            if row:
                embedding_text = f"{row['category']} {row['entity_type']} {row['entity_name'] or ''} {content}"
                embedding = await self._generate_embedding(embedding_text)
                embedding_str = f"[{','.join(map(str, embedding))}]"
                updates.append(f"embedding = ${param_count}::vector")
                params.append(embedding_str)
                param_count += 1

        if importance is not None:
            updates.append(f"importance = ${param_count}")
            params.append(importance)
            param_count += 1

        if metadata is not None:
            updates.append(f"metadata = ${param_count}")
            params.append(json.dumps(metadata))
            param_count += 1

        if not updates:
            return None

        params.append(memory_id)
        query = f"""
            UPDATE user_memories
            SET {', '.join(updates)}
            WHERE id = ${param_count}
            RETURNING id, user_id, category, entity_type, entity_name, content,
                      importance, metadata, created_at, updated_at
        """

        row = await DatabaseConnection.fetchrow(query, *params)

        if row:
            logger.info("Memória atualizada", memory_id=memory_id)
            return Memory(
                id=row["id"],
                user_id=row["user_id"],
                category=row["category"],
                entity_type=row["entity_type"],
                entity_name=row["entity_name"],
                content=row["content"],
                importance=row["importance"],
                metadata=dict(row["metadata"]) if row["metadata"] else {},
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        return None

    async def delete_memory(self, memory_id: int) -> bool:
        """Marca uma memória como inativa (soft delete)."""
        result = await DatabaseConnection.execute(
            "UPDATE user_memories SET is_active = FALSE WHERE id = $1",
            memory_id,
        )
        deleted = result == "UPDATE 1"
        if deleted:
            logger.info("Memória eliminada", memory_id=memory_id)
        return deleted

    async def search_memories(
        self,
        user_id: str,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> List[Memory]:
        """Busca memórias semanticamente similares."""
        embedding = await self._generate_embedding(query)
        embedding_str = f"[{','.join(map(str, embedding))}]"

        category_filter = ""
        params = [user_id, embedding_str, min_similarity, limit]

        if category:
            category_filter = "AND category = $5"
            params.append(category)

        rows = await DatabaseConnection.fetch(
            f"""
            SELECT
                id, user_id, category, entity_type, entity_name, content,
                importance, metadata, created_at, updated_at,
                1 - (embedding <=> $2::vector) as similarity
            FROM user_memories
            WHERE user_id = $1
              AND is_active = TRUE
              AND 1 - (embedding <=> $2::vector) >= $3
              {category_filter}
            ORDER BY similarity DESC
            LIMIT $4
            """,
            *params,
        )

        memories = []
        for row in rows:
            memories.append(
                Memory(
                    id=row["id"],
                    user_id=row["user_id"],
                    category=row["category"],
                    entity_type=row["entity_type"],
                    entity_name=row["entity_name"],
                    content=row["content"],
                    importance=row["importance"],
                    metadata=dict(row["metadata"]) if row["metadata"] else {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    similarity_score=float(row["similarity"]),
                )
            )

        logger.info(
            "Busca de memórias concluída",
            user_id=user_id,
            query=query[:50],
            results=len(memories),
        )
        return memories

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Obtém o perfil consolidado do utilizador com todas as memórias ativas."""
        await self.ensure_user_exists(user_id)

        profile_row = await DatabaseConnection.fetchrow(
            "SELECT name, location, created_at FROM user_profiles WHERE user_id = $1",
            user_id,
        )

        memories = await DatabaseConnection.fetch(
            """
            SELECT category, entity_type, entity_name, content, importance
            FROM user_memories
            WHERE user_id = $1 AND is_active = TRUE
            ORDER BY category, importance DESC
            """,
            user_id,
        )

        # Organizar memórias por categoria
        categorized: Dict[str, List[Dict]] = {}
        for row in memories:
            cat = row["category"]
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(
                {
                    "tipo": row["entity_type"],
                    "nome": row["entity_name"],
                    "info": row["content"],
                    "importancia": row["importance"],
                }
            )

        return {
            "user_id": user_id,
            "nome": profile_row["name"] if profile_row else None,
            "localizacao": profile_row["location"] if profile_row else None,
            "membro_desde": (
                profile_row["created_at"].isoformat() if profile_row else None
            ),
            "memorias": categorized,
        }

    async def save_episode(
        self,
        user_id: str,
        session_id: str,
        summary: str,
        key_topics: List[str],
        emotional_tone: str,
        started_at: datetime,
        duration_minutes: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Guarda um episódio de conversa."""
        await self.ensure_user_exists(user_id)

        embedding = await self._generate_embedding(summary)
        embedding_str = f"[{','.join(map(str, embedding))}]"

        row = await DatabaseConnection.fetchrow(
            """
            INSERT INTO conversation_episodes
            (user_id, session_id, summary, key_topics, emotional_tone,
             embedding, started_at, duration_minutes, metadata)
            VALUES ($1, $2, $3, $4, $5, $6::vector, $7, $8, $9)
            RETURNING id
            """,
            user_id,
            session_id,
            summary,
            key_topics,
            emotional_tone,
            embedding_str,
            started_at,
            duration_minutes,
            json.dumps(metadata or {}),
        )

        logger.info(
            "Episódio de conversa guardado",
            user_id=user_id,
            session_id=session_id,
            episode_id=row["id"],
        )
        return row["id"]

    async def get_recent_episodes(
        self, user_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Obtém os episódios de conversa mais recentes."""
        rows = await DatabaseConnection.fetch(
            """
            SELECT session_id, summary, key_topics, emotional_tone,
                   started_at, ended_at, duration_minutes
            FROM conversation_episodes
            WHERE user_id = $1
            ORDER BY ended_at DESC
            LIMIT $2
            """,
            user_id,
            limit,
        )

        return [
            {
                "session_id": row["session_id"],
                "resumo": row["summary"],
                "topicos": row["key_topics"],
                "tom_emocional": row["emotional_tone"],
                "inicio": row["started_at"].isoformat() if row["started_at"] else None,
                "fim": row["ended_at"].isoformat() if row["ended_at"] else None,
                "duracao_minutos": row["duration_minutes"],
            }
            for row in rows
        ]
