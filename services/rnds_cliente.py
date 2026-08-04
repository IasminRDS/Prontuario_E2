# -*- coding: utf-8 -*-
"""Cliente da RNDS (Rede Nacional de Dados em Saúde).

A RNDS exige TLS **mútuo**: o estabelecimento se identifica com certificado
ICP-Brasil, troca esse certificado por um token no serviço de autenticação e só
então envia os recursos FHIR ao serviço de EHR. São dois hosts distintos e o
token tem validade curta, então ele é mantido em memória e renovado sozinho.

Sem certificado configurado, o módulo entrega um cliente **simulado** — que
devolve protocolo sintético e deixa isso explícito no protocolo (`SIM-`). É o
que mantém o ambiente de demonstração funcionando sem fingir que houve envio.

Os nomes de cabeçalho e os caminhos variam entre versões do manual da RNDS, por
isso são configuráveis por variável de ambiente. Confira contra o manual vigente
antes de apontar para produção.
"""
import hashlib
import json
import os
import threading
import time

import requests


class ErroRnds(Exception):
    """Base — nunca levantada diretamente."""


class RndsIndisponivel(ErroRnds):
    """Falha transitória: rede, timeout, 5xx, token expirado.

    Vale retentar; o envio continua pendente na fila.
    """


class RndsRejeitou(ErroRnds):
    """A RNDS entendeu e recusou: 4xx de validação, recurso malformado.

    Retentar o mesmo conteúdo dá o mesmo erro — o envio vira definitivo.
    """


def _env(nome, padrao=None):
    valor = os.getenv(nome, padrao)
    return valor.strip() if isinstance(valor, str) else valor


def chave_idempotencia(tipo, tabela, entidade_id, payload):
    """Impressão digital do conteúdo enviado.

    Serve para dois fins: impedir que o mesmo documento entre duas vezes na fila
    e permitir que a RNDS descarte reenvio duplicado depois de uma resposta
    perdida no meio do caminho — o caso em que o registro chegou mas nós não
    soubemos.
    """
    bruto = f"{tipo}|{tabela}|{entidade_id}|{payload}"
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


class ClienteSimulado:
    """Devolve protocolo sintético, sem tocar a rede."""

    configurado = False
    simulado = True

    def enviar(self, tipo, recurso, chave):
        return f"SIM-{chave[:16].upper()}"


class ClienteRnds:
    """Cliente real. Instancie por processo — o token é compartilhado."""

    configurado = True
    simulado = False

    def __init__(self):
        self.url_auth = _env("RNDS_AUTH_URL")
        self.url_ehr = _env("RNDS_EHR_URL")
        self.certificado = _env("RNDS_CERTIFICADO")
        self.chave_privada = _env("RNDS_CHAVE_PRIVADA")
        self.requisitante = _env("RNDS_REQUISITANTE_CNS")
        self.timeout = int(_env("RNDS_TIMEOUT", "30"))
        # O cabeçalho do token mudou de nome entre versões do manual.
        self.cabecalho_token = _env("RNDS_CABECALHO_TOKEN", "Authorization")

        self._token = None
        self._token_expira_em = 0.0
        self._trava = threading.Lock()

    # ------------------------------------------------------------ autenticação
    def _cert(self):
        """Par (cert, chave) para o mTLS, ou só o caminho de um PEM combinado."""
        if self.chave_privada:
            return (self.certificado, self.chave_privada)
        return self.certificado

    def _obter_token(self):
        """Token JWT, renovado com folga antes de expirar."""
        with self._trava:
            if self._token and time.time() < self._token_expira_em:
                return self._token

            try:
                resposta = requests.post(
                    self.url_auth, cert=self._cert(), timeout=self.timeout,
                    headers={"Accept": "application/json"},
                )
            except requests.RequestException as exc:
                raise RndsIndisponivel(f"falha ao autenticar: {exc}") from exc

            if resposta.status_code >= 500:
                raise RndsIndisponivel(
                    f"serviço de autenticação indisponível ({resposta.status_code})")
            if resposta.status_code >= 400:
                # Certificado inválido, vencido ou sem permissão: retentar não
                # resolve, mas também não é culpa do documento — tratamos como
                # indisponibilidade para não marcar o envio como recusado.
                raise RndsIndisponivel(
                    f"autenticação recusada ({resposta.status_code}): "
                    f"{resposta.text[:200]}")

            try:
                corpo = resposta.json()
            except ValueError:
                corpo = {}
            token = corpo.get("access_token") or resposta.text.strip()
            if not token:
                raise RndsIndisponivel("autenticação não devolveu token")

            # Renova 60s antes do vencimento declarado.
            validade = int(corpo.get("expires_in") or 300)
            self._token = token
            self._token_expira_em = time.time() + max(validade - 60, 30)
            return self._token

    def invalidar_token(self):
        with self._trava:
            self._token = None
            self._token_expira_em = 0.0

    # ------------------------------------------------------------------ envio
    def enviar(self, tipo, recurso, chave):
        """Envia um recurso FHIR. Devolve o protocolo da RNDS.

        Levanta `RndsIndisponivel` (retentável) ou `RndsRejeitou` (definitivo).
        """
        token = self._obter_token()
        destino = f"{self.url_ehr.rstrip('/')}/{tipo}"
        cabecalhos = {
            self.cabecalho_token: token,
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json",
            # Deixa a RNDS descartar reenvio do mesmo conteúdo.
            "X-Idempotency-Key": chave,
        }
        if self.requisitante:
            cabecalhos["X-Requisitante"] = self.requisitante

        try:
            resposta = requests.post(
                destino, data=json.dumps(recurso, ensure_ascii=False).encode("utf-8"),
                headers=cabecalhos, cert=self._cert(), timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise RndsIndisponivel(f"falha de transporte: {exc}") from exc

        if resposta.status_code in (401, 403):
            # Token pode ter expirado antes do prazo declarado.
            self.invalidar_token()
            raise RndsIndisponivel(
                f"não autorizado ({resposta.status_code}) — token descartado")
        if resposta.status_code == 429 or resposta.status_code >= 500:
            raise RndsIndisponivel(f"RNDS indisponível ({resposta.status_code})")
        if resposta.status_code >= 400:
            raise RndsRejeitou(
                f"recusado ({resposta.status_code}): {resposta.text[:400]}")

        return _protocolo(resposta) or chave[:16].upper()


def _protocolo(resposta):
    """Protocolo devolvido pela RNDS, onde quer que ele venha."""
    for cabecalho in ("X-Protocolo", "Location", "ETag"):
        valor = resposta.headers.get(cabecalho)
        if valor:
            return valor.rsplit("/", 1)[-1][:80]
    try:
        corpo = resposta.json()
    except ValueError:
        return None
    if isinstance(corpo, dict):
        for campo in ("id", "protocolo", "identifier"):
            if corpo.get(campo):
                return str(corpo[campo])[:80]
    return None


_cliente = None
_trava_modulo = threading.Lock()


def esta_configurado():
    return bool(_env("RNDS_AUTH_URL") and _env("RNDS_EHR_URL")
                and _env("RNDS_CERTIFICADO"))


def obter_cliente(forcar_novo=False):
    """Cliente real se houver certificado configurado; simulado caso contrário."""
    global _cliente
    with _trava_modulo:
        if forcar_novo or _cliente is None:
            _cliente = ClienteRnds() if esta_configurado() else ClienteSimulado()
        return _cliente
