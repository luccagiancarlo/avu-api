"""Repositório de candidato (login + lookup).

As tabelas `cvu.ve_candidato_all` e `cvu.pa_candidato_all` são externas (views
do CVU). Não temos `Base` model para elas — usamos `text()` parametrizado.

Comportamento do legado (`CandidatoDAO.getCandidato`, linhas 211-230):
- Trunca senha em 8 chars e compara `UPPER(SUBSTR(de_senha, 1, 8))`.
- Distingue VE (vestibular) de PA (PAS) pelo tamanho do nu_inscricao da request:
  o legado decide pelo `tp_evento` do evento ativo, mas em `enviarEmailEsqueceuSenha`
  usa `nu_inscricao.length() > 6` → PAS. Replicamos esse critério mais simples.
- A chave de match é `(nu_inscricao || dv_inscricao) = :inscr_completa` — ou seja,
  o cliente manda os dígitos concatenados.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class CandidatoAutenticado:
    nu_inscricao: int
    dv_inscricao: int
    nm_candidato: str
    nu_cpf: str
    tp_evento: str  # "VE" ou "PA"


def _is_pas(inscr_completa: str) -> bool:
    return len(inscr_completa) > 6


def _tabela(inscr_completa: str) -> str:
    return "cvu.pa_candidato_all" if _is_pas(inscr_completa) else "cvu.ve_candidato_all"


async def autenticar(
    session: AsyncSession,
    *,
    inscr_completa: str,
    senha: str,
) -> CandidatoAutenticado | None:
    """Retorna candidato se credenciais válidas, None caso contrário.

    `inscr_completa` é `nu_inscricao || dv_inscricao` (string de dígitos).
    `senha` é truncada em 8 chars e comparada case-insensitive — mesmo critério do legado.
    """
    senha_trunc = senha[:8].upper()
    tabela = _tabela(inscr_completa)
    tp_evento = "PA" if _is_pas(inscr_completa) else "VE"

    sql = text(
        f"""
        SELECT a.nu_inscricao, a.dv_inscricao, a.nm_candidato, a.nu_cpf
          FROM {tabela} a
         WHERE (a.nu_inscricao || a.dv_inscricao) = :inscr
           AND UPPER(SUBSTR(a.de_senha, 1, 8)) = :senha
        """
    )
    result = await session.execute(sql, {"inscr": inscr_completa, "senha": senha_trunc})
    row = result.first()
    if row is None:
        return None

    return CandidatoAutenticado(
        nu_inscricao=int(row[0]),
        dv_inscricao=int(row[1]),
        nm_candidato=str(row[2]).strip(),
        nu_cpf=str(row[3]).strip(),
        tp_evento=tp_evento,
    )


async def buscar_email_para_recuperacao(
    session: AsyncSession, *, inscr_completa: str
) -> tuple[str, str, str] | None:
    """Retorna (nm_candidato, en_email, de_senha) para envio de email "esqueceu a senha".

    Equivale a `LoginResource.enviarEmailEsqueceuSenha` (linhas 116-118).
    Retorna None se inscrição não existe.
    """
    tabela = _tabela(inscr_completa)
    sql = text(
        f"""
        SELECT nm_candidato, en_email, de_senha
          FROM {tabela}
         WHERE (nu_inscricao || dv_inscricao) = :inscr
        """
    )
    result = await session.execute(sql, {"inscr": inscr_completa})
    row = result.first()
    if row is None:
        return None
    return str(row[0]).strip(), str(row[1]).strip(), str(row[2]).strip()
