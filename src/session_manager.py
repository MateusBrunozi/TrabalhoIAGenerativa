"""
session_manager.py  –  Gerencia histórico e estado de seleção por usuário.

Estados do fluxo:
  "aguardando_marca"   → usuário ainda não escolheu a marca
  "aguardando_modelo"  → marca escolhida, aguarda o modelo
  "ativo"              → hardware selecionado, diagnóstico em andamento
"""

from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional

from config.settings import MAX_HISTORY


@dataclass
class UserSession:
    historico:      list[dict]       = field(default_factory=list)
    estado:         str              = "aguardando_marca"   # ver docstring
    marca:          Optional[str]    = None   # ex: "MSI"
    modelo:         Optional[str]    = None   # ex: "MSI_B550_TOMAHAWK"
    modelo_desc:    Optional[str]    = None   # ex: "MSI MAG B550 Tomahawk (AMD AM4)"
    filtro_rag:     list[str]        = field(default_factory=list)
    ultima_ativ:    datetime         = field(default_factory=datetime.now)

    def reset(self):
        """Reinicia a sessão mantendo apenas o chat_id."""
        self.historico   = []
        self.estado      = "aguardando_marca"
        self.marca       = None
        self.modelo      = None
        self.modelo_desc = None
        self.filtro_rag  = []
        self.ultima_ativ = datetime.now()


class SessionManager:
    SESSION_TTL_HOURS = 2

    def __init__(self):
        self._sessions: dict[int, UserSession] = {}
        self._lock = Lock()

    # ── Acesso / criação de sessão ───────────────────────────────────────────

    def get_or_create(self, chat_id: int) -> UserSession:
        with self._lock:
            self._cleanup_expired()
            if chat_id not in self._sessions:
                self._sessions[chat_id] = UserSession()
            return self._sessions[chat_id]

    def clear(self, chat_id: int):
        with self._lock:
            if chat_id in self._sessions:
                self._sessions[chat_id].reset()

    # ── Estado do fluxo ──────────────────────────────────────────────────────

    def set_marca(self, chat_id: int, marca: str):
        s = self.get_or_create(chat_id)
        s.marca        = marca
        s.estado       = "aguardando_modelo"
        s.ultima_ativ  = datetime.now()

    def set_modelo(self, chat_id: int, modelo: str, desc: str, filtro: list[str]):
        s = self.get_or_create(chat_id)
        s.modelo       = modelo
        s.modelo_desc  = desc
        s.filtro_rag   = filtro
        s.estado       = "ativo"
        s.ultima_ativ  = datetime.now()

    # ── Histórico de mensagens ───────────────────────────────────────────────

    def add_message(self, chat_id: int, role: str, content: str):
        s = self.get_or_create(chat_id)
        s.historico.append({"role": role, "content": content})
        s.ultima_ativ = datetime.now()
        # Mantém apenas as últimas MAX_HISTORY trocas
        if len(s.historico) > MAX_HISTORY * 2:
            s.historico = s.historico[-(MAX_HISTORY * 2):]

    def get_history(self, chat_id: int) -> list[dict]:
        return list(self.get_or_create(chat_id).historico)

    def session_length(self, chat_id: int) -> int:
        return len(self.get_or_create(chat_id).historico)

    # ── Limpeza ──────────────────────────────────────────────────────────────

    def _cleanup_expired(self):
        threshold = datetime.now() - timedelta(hours=self.SESSION_TTL_HOURS)
        expired = [
            cid for cid, s in self._sessions.items()
            if s.ultima_ativ < threshold
        ]
        for cid in expired:
            del self._sessions[cid]
