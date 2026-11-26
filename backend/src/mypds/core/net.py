"""Client HTTP sortant avec protection SSRF (voir ADR-0009 et SECURITY.md § 6).

Politique « Internet » : toute adresse résolue doit être publique, sauf si l'hôte figure
dans MYPDS_OUTBOUND_ALLOW_HOSTS. La connexion se fait vers l'IP validée (pas de DNS
rebinding), avec SNI et en-tête Host d'origine. Les redirections sont re-validées.
"""

import asyncio
import base64
import hashlib
import ipaddress
import os
import socket
import ssl
import tempfile
from dataclasses import dataclass

import httpx

from mypds.core.settings import get_settings

USER_AGENT = "MyPersonalDigitalSpace/0.1 (+self-hosted)"
_REDIRECTS = {301, 302, 303, 307, 308}


class OutboundError(Exception):
    """Erreur lisible par l'utilisateur lors d'un appel sortant."""


class OutboundBlocked(OutboundError):
    pass


@dataclass(slots=True)
class FetchResult:
    status: int
    headers: httpx.Headers
    content: bytes
    url: str


IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


def is_public_ip(ip: IPAddress) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def _host_allowed_internal(host: str) -> bool:
    allow = {h.lower().rstrip(".") for h in get_settings().outbound_allow_hosts}
    return host.lower().rstrip(".") in allow


async def resolve_checked(host: str, port: int, allow_private: bool = False) -> IPAddress:
    """Résout `host` et refuse si une adresse n'est pas autorisée. Renvoie l'IP à utiliser."""
    allow_internal = allow_private or _host_allowed_internal(host)
    try:
        ips: list[IPAddress] = [ipaddress.ip_address(host)]
    except ValueError:
        loop = asyncio.get_running_loop()
        try:
            infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise OutboundError(f"Nom d'hôte introuvable : {host}") from exc
        ips = [ipaddress.ip_address(info[4][0]) for info in infos]
    if not ips:
        raise OutboundError(f"Nom d'hôte introuvable : {host}")
    if not allow_internal:
        for ip in ips:
            if not is_public_ip(ip):
                raise OutboundBlocked(
                    f"Adresse non autorisée pour {host} ({ip}). "
                    "Un administrateur peut l'ajouter à MYPDS_OUTBOUND_ALLOW_HOSTS."
                )
    # Préférence IPv4 pour la compatibilité des réseaux domestiques
    ips.sort(key=lambda i: i.version)
    return ips[0]


def normalize_fingerprint(value: str) -> str:
    """« AB:CD:… » ou « abcd… » → 64 caractères hexadécimaux minuscules."""
    fp = value.replace(":", "").replace(" ", "").lower()
    if len(fp) != 64 or any(c not in "0123456789abcdef" for c in fp):
        raise OutboundError("Empreinte TLS invalide : SHA-256 attendue (64 caractères hexadécimaux)")
    return fp


def _check_fingerprint(response: httpx.Response, pin: str) -> None:
    stream = response.extensions.get("network_stream")
    ssl_obj = stream.get_extra_info("ssl_object") if stream is not None else None
    der = ssl_obj.getpeercert(binary_form=True) if ssl_obj is not None else None
    if not der or hashlib.sha256(der).hexdigest() != pin:
        raise OutboundError("Empreinte du certificat TLS inattendue : connexion refusée")


def validate_url(url: str) -> httpx.URL:
    try:
        u = httpx.URL(url)
    except Exception as exc:  # noqa: BLE001
        raise OutboundError("URL invalide") from exc
    if u.scheme not in ("http", "https"):
        raise OutboundError("Seuls les schémas http et https sont acceptés")
    if not u.host:
        raise OutboundError("URL sans nom d'hôte")
    if u.userinfo:
        raise OutboundError("Les identifiants dans l'URL ne sont pas acceptés")
    return u


def _root_cause(exc: BaseException) -> str:
    """Message httpx + cause système la plus profonde (« [Errno 65] No route to host »…), utile au diagnostic."""
    msg = str(exc).strip() or type(exc).__name__
    seen: set[int] = set()
    cur: BaseException | None = exc
    deepest: BaseException | None = None
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, OSError) or (cur is not exc and str(cur).strip()):
            deepest = cur
        nested = getattr(cur, "exceptions", None)  # ExceptionGroup (plusieurs adresses essayées)
        cur = cur.__cause__ or cur.__context__ or (nested[0] if nested else None)
    if deepest is not None and str(deepest).strip() and str(deepest).strip() != msg:
        return f"{msg} ({str(deepest).strip()})"
    return msg


@dataclass(frozen=True, slots=True)
class ClientTls:
    """TLS mutuel (ex. Docker `--tlsverify`) : autorité qui a signé le serveur + certificat client."""

    ca_pem: str
    cert_pem: str
    key_pem: str

    def context(self) -> ssl.SSLContext:
        try:
            ctx = ssl.create_default_context(cadata=self.ca_pem)
        except (ssl.SSLError, ValueError) as exc:
            raise OutboundError("Certificat d'autorité (CA) illisible : collez le contenu PEM de ca.pem") from exc
        # load_cert_chain exige des fichiers : dossier privé temporaire, effacé aussitôt
        with tempfile.TemporaryDirectory(prefix="mypds-tls-") as d:
            cert, key = os.path.join(d, "cert.pem"), os.path.join(d, "key.pem")
            for path, data in ((cert, self.cert_pem), (key, self.key_pem)):
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as f:
                    f.write(data)
            try:
                ctx.load_cert_chain(cert, key)
            except (ssl.SSLError, ValueError) as exc:
                raise OutboundError(
                    "Certificat ou clé client illisible : collez le contenu PEM de cert.pem et key.pem"
                ) from exc
        return ctx


async def fetch(
    url: str,
    *,
    max_bytes: int,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
    max_redirects: int = 3,
    basic_auth: tuple[str, str] | None = None,
    allow_private: bool = False,
    tls_fingerprint: str | None = None,
    client_tls: ClientTls | None = None,
) -> FetchResult:
    """`basic_auth` n'est envoyé qu'en HTTPS et uniquement à l'hôte d'origine (jamais après une
    redirection vers un autre hôte), pour ne pas divulguer d'identifiants.

    Politique « infrastructure » (connecteurs) : `allow_private=True` autorise une adresse privée,
    à condition que l'hôte ait été fixé par un administrateur ; `tls_fingerprint` (SHA-256 du
    certificat) remplace la vérification par autorité pour les certificats auto-signés.
    """
    current = validate_url(url)
    origin_host = current.host
    if basic_auth and current.scheme != "https":
        raise OutboundError("Identifiants refusés sur une connexion non chiffrée : utilisez https://")
    base_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    verify: ssl.SSLContext | bool = True
    pin = normalize_fingerprint(tls_fingerprint) if tls_fingerprint else None
    if client_tls:
        verify = client_tls.context()  # TLS mutuel : autorité privée + certificat client (Docker)
    elif pin:
        verify = ssl.create_default_context()
        verify.check_hostname = False
        verify.verify_mode = ssl.CERT_NONE  # compensé par la comparaison d'empreinte ci-dessous
    async with httpx.AsyncClient(
        trust_env=False, follow_redirects=False, timeout=httpx.Timeout(timeout), verify=verify
    ) as client:
        for _ in range(max_redirects + 1):
            port = current.port or (443 if current.scheme == "https" else 80)
            ip = await resolve_checked(current.host, port, allow_private=allow_private)
            target = current.copy_with(host=str(ip))
            req_headers = dict(base_headers)
            req_headers["Host"] = current.netloc.decode()
            if basic_auth and current.scheme == "https" and current.host == origin_host:
                token = base64.b64encode(f"{basic_auth[0]}:{basic_auth[1]}".encode()).decode()
                req_headers["Authorization"] = f"Basic {token}"
            extensions = {"sni_hostname": current.host} if current.scheme == "https" else {}
            request = client.build_request("GET", target, headers=req_headers, extensions=extensions)
            try:
                response = await client.send(request, stream=True)
            except httpx.TimeoutException as exc:
                raise OutboundError("Délai dépassé") from exc
            except httpx.HTTPError as exc:
                cause = _root_cause(exc)
                raise OutboundError(f"Connexion impossible : {cause[:200]}") from exc
            try:
                if pin is not None:
                    _check_fingerprint(response, pin)
                if response.status_code in _REDIRECTS and "location" in response.headers:
                    current = validate_url(str(current.join(response.headers["location"])))
                    continue
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise OutboundError(f"Réponse trop volumineuse (> {max_bytes // 1024} Ko)")
                    chunks.append(chunk)
                return FetchResult(response.status_code, response.headers, b"".join(chunks), str(current))
            finally:
                await response.aclose()
    raise OutboundError("Trop de redirections")
