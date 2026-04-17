"""
Collect translatable msgids without GNU gettext (makemessages).
Used by bootstrap_i18n to build django.po / django.mo via polib.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from django.conf import settings

# GNU Plural-Forms headers (gettext) per Django language code.
PLURAL_FORMS: dict[str, str] = {
    "en": "nplurals=2; plural=(n != 1);",
    "pa": "nplurals=2; plural=(n != 1);",
    "pl": "nplurals=3; plural=(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<12 || n%100>14) ? 1 : 2);",
    "ur": "nplurals=2; plural=(n != 1);",
    "ro": "nplurals=3; plural=(n==1 ? 0 : n==0 || (n!=1 && n%100>=1 && n%100<=19) ? 1 : 2);",
    "bn": "nplurals=2; plural=(n != 1);",
    "gu": "nplurals=2; plural=(n != 1);",
    "ar": "nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5);",
    "zh-hans": "nplurals=1; plural=0;",
    "so": "nplurals=2; plural=(n != 1);",
}

# deep_translator GoogleTranslate target language codes.
GOOGLE_TARGET_BY_DJANGO_LANG: dict[str, str] = {
    "pa": "pa",
    "pl": "pl",
    "ur": "ur",
    "ro": "ro",
    "bn": "bn",
    "gu": "gu",
    "ar": "ar",
    "zh-hans": "zh-CN",
    "so": "so",
}

# blocktrans / interpolated strings (must match Django gettext msgids).
BLOCKTRANS_MSGIDS: tuple[str, ...] = (
    "Regional moments from public Flickr feeds \u2014 each tile links to the photographer\u2019s page.",
    "Like a well-planned neighbourhood, this platform is designed around how people actually live \u2014 quick routes to food support, housing advice, recovery services, activities, and the organisations that make our towns and cities kinder.",
    "These pathways are for people who need a bit more specific guidance. They're written in plain language and connect you directly to organisations in the West Midlands that can help. You don't need a referral to use this section \u2014 just find what's relevant to you and reach out.",
    "Go to %(title)s pathway",
    "Your profile is %(score)s%% complete. A fuller profile helps people find you.",
    "I consent to my information being shared with %(org_name)s for the purpose of receiving support. I understand this data will be stored securely and handled in accordance with GDPR.",
    "%(count)s sections",
)

TRANS_DOUBLE = re.compile(r'{%\s*trans\s+"((?:\\.|[^"])*)"\s*%}')
TRANS_SINGLE = re.compile(r"{%\s*trans\s+'((?:\\.|[^'])*)'\s*%}")


def _string_from_ast_expr(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _string_from_ast_expr(node.left), _string_from_ast_expr(node.right)
        if left is not None and right is not None:
            return left + right
        return None
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            else:
                return None
        return "".join(parts)
    return None


class _GettextCallVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.strings: set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_func_basename(node.func)
        if name in ("_", "gettext", "gettext_lazy", "ugettext", "ugettext_lazy"):
            if node.args:
                s = _string_from_ast_expr(node.args[0])
                if s:
                    self.strings.add(s)
        self.generic_visit(node)


def _call_func_basename(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def extract_from_python_file(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return set()
    visitor = _GettextCallVisitor()
    visitor.visit(tree)
    return visitor.strings


def extract_from_template_file(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    found: set[str] = set()
    for m in TRANS_DOUBLE.finditer(text):
        found.add(m.group(1))
    for m in TRANS_SINGLE.finditer(text):
        found.add(m.group(1))
    return found


def collect_all_msgids() -> list[str]:
    base: Path = settings.BASE_DIR
    msgids: set[str] = set(BLOCKTRANS_MSGIDS)

    tpl_root = base / "templates"
    if tpl_root.is_dir():
        for path in tpl_root.rglob("*.html"):
            msgids |= extract_from_template_file(path)

    apps_root = base / "apps"
    if apps_root.is_dir():
        for path in apps_root.rglob("*.py"):
            if "migrations" in path.parts or path.name == "i18n_catalog.py":
                continue
            # Model / field verbose_name strings explode catalog size and are mostly
            # admin-only; ship UI strings first. Re-include later via gettext makemessages.
            if path.name == "models.py":
                continue
            rel = path.as_posix()
            if "/tests/" in rel or rel.endswith("/tests.py") or path.name.startswith("test_"):
                continue
            msgids |= extract_from_python_file(path)

    for path in (base / "config").rglob("*.py"):
        msgids |= extract_from_python_file(path)

    msgids.discard("")
    return sorted(msgids)
