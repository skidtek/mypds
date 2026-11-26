"""Lecture SNMP v3 (authPriv) minimale : GET de valeurs et parcours de tables. Aucune écriture (SET)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pysnmp.hlapi.v3arch.asyncio import (
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    UsmUserData,
    bulk_walk_cmd,
    get_cmd,
    usmAesCfb128Protocol,
    usmDESPrivProtocol,
    usmHMAC192SHA256AuthProtocol,
    usmHMACMD5AuthProtocol,
    usmHMACSHAAuthProtocol,
)
from pysnmp.proto.rfc1902 import Counter32, Counter64, Gauge32, Integer, Integer32, OctetString, Unsigned32

AUTH = {"SHA": usmHMACSHAAuthProtocol, "SHA256": usmHMAC192SHA256AuthProtocol, "MD5": usmHMACMD5AuthProtocol}
PRIV = {"AES": usmAesCfb128Protocol, "DES": usmDESPrivProtocol}
MAX_ROWS = 2000


class SnmpError(Exception):
    pass


@dataclass(slots=True)
class Credentials:
    user: str
    auth_key: str
    priv_key: str
    auth: str = "SHA"
    priv: str = "AES"

    def usm(self) -> UsmUserData:
        return UsmUserData(
            self.user, self.auth_key, self.priv_key, authProtocol=AUTH[self.auth], privProtocol=PRIV[self.priv]
        )


def _py(v: Any) -> Any:
    if isinstance(v, (Integer, Integer32, Counter32, Counter64, Gauge32, Unsigned32)):
        return int(v)
    if isinstance(v, OctetString):
        return v.asOctets().decode("utf-8", "replace")
    return None  # noSuchObject / noSuchInstance / endOfMibView


async def _target(host: str, port: int) -> UdpTransportTarget:
    try:
        return await UdpTransportTarget.create((host, port), timeout=3, retries=1)
    except Exception as exc:  # noqa: BLE001 - résolution DNS, etc.
        raise SnmpError(f"Adresse SNMP injoignable : {exc}") from exc


def _check(err_ind: Any, err_stat: Any) -> None:
    if err_ind:
        msg = str(err_ind)
        if "timeout" in msg.lower() or "No SNMP response" in msg:
            raise SnmpError("Pas de réponse SNMP : vérifiez l'adresse, le port 161/UDP et que SNMP v3 est activé")
        if (
            "wrong" in msg.lower()
            or "unknown" in msg.lower()
            or "authentication" in msg.lower()
            or "decrypt" in msg.lower()
        ):
            raise SnmpError(f"Identifiants SNMP v3 refusés : {msg}")
        raise SnmpError(f"Erreur SNMP : {msg}")
    if err_stat:
        raise SnmpError(f"Erreur SNMP : {err_stat.prettyPrint()}")


async def get(host: str, port: int, cred: Credentials, oids: dict[str, str]) -> dict[str, Any]:
    engine = SnmpEngine()
    try:
        target = await _target(host, port)
        err_ind, err_stat, _idx, binds = await get_cmd(
            engine, cred.usm(), target, ContextData(), *(ObjectType(ObjectIdentity(o)) for o in oids.values())
        )
        _check(err_ind, err_stat)
        values = {str(name): _py(val) for name, val in binds}
        return {k: values.get(o) for k, o in oids.items()}
    finally:
        engine.close_dispatcher()


async def table(host: str, port: int, cred: Credentials, entry_oid: str) -> dict[str, dict[int, Any]]:
    """Parcourt `<entry_oid>.<colonne>.<index>` → {index: {colonne: valeur}}."""
    engine = SnmpEngine()
    rows: dict[str, dict[int, Any]] = {}
    prefix = entry_oid + "."
    try:
        target = await _target(host, port)
        n = 0
        async for err_ind, err_stat, _idx, binds in bulk_walk_cmd(
            engine,
            cred.usm(),
            target,
            ContextData(),
            0,
            25,
            ObjectType(ObjectIdentity(entry_oid)),
            lexicographicMode=False,
        ):
            _check(err_ind, err_stat)
            for name, val in binds:
                oid = str(name)
                if not oid.startswith(prefix):
                    continue
                col, _, index = oid[len(prefix) :].partition(".")
                rows.setdefault(index, {})[int(col)] = _py(val)
                n += 1
            if n > MAX_ROWS:
                break
        return rows
    finally:
        engine.close_dispatcher()
