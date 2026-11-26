"""Chaque message d'erreur écrit par le serveur doit avoir sa traduction dans frontend/src/i18n/server.ts.

Le serveur répond en français ; l'interface anglaise traduit ces messages d'après ce catalogue.
Un message ajouté sans traduction s'afficherait en français : ce test le signale.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backend/src/mypds"
CATALOG = ROOT / "frontend/src/i18n/server.ts"
CALLS = {
    "problem",
    "ConnectorError",
    "ValueError",
    "OutboundError",
    "OutboundBlocked",
    "FeedParseError",
    "SnmpError",
    "CalendarError",
    "SecretKeyError",
}


def _template(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in node.values)
    return None


def server_messages() -> set[str]:
    found: set[str] = set()
    for path in SRC.rglob("*.py"):
        if "migrations" in path.parts:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                args = [a for a in node.args if not (isinstance(a, ast.Constant) and isinstance(a.value, int))]
                if name in CALLS and args and (t := _template(args[0])) is not None:
                    found.add(t)
            # Messages de validation composés par connectors.sdk.readable() et libellés des champs
            if isinstance(node, ast.FunctionDef) and node.name == "readable":
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and getattr(sub.func, "attr", None) == "append" and sub.args:
                        arg = sub.args[0]
                        for expr in (arg.body, arg.orelse) if isinstance(arg, ast.IfExp) else (arg,):
                            t = _template(expr)
                            if t and t != "{}":
                                found.add(t)
            if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "FIELD_LABELS" for t in node.targets):
                found.update(v.value for v in node.value.values if isinstance(v, ast.Constant))
    return found


def catalog_keys() -> set[str]:
    text = CATALOG.read_text()
    body = text[text.index("SERVER_EN") : text.index("\n}\n")]
    return set(re.findall(r'^\s*"((?:[^"\\]|\\.)*)":', body, flags=re.M))


def test_every_server_message_has_an_english_translation() -> None:
    missing = sorted(server_messages() - catalog_keys())
    assert not missing, "À traduire dans frontend/src/i18n/server.ts :\n" + "\n".join(missing)


def test_no_obsolete_translation() -> None:
    orphans = sorted(catalog_keys() - server_messages())
    assert not orphans, "Traductions sans message côté serveur (à retirer) :\n" + "\n".join(orphans)
