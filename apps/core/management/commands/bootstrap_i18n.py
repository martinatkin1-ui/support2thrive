"""
Build locale/<lang>/LC_MESSAGES/django.{po,mo} without GNU gettext.

Run once after template changes (or in CI):
  python manage.py bootstrap_i18n --translate

Requires: polib, deep-translator (optional; only with --translate).
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import polib
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import to_locale

from apps.core.i18n_catalog import (
    GOOGLE_TARGET_BY_DJANGO_LANG,
    PLURAL_FORMS,
    collect_all_msgids,
)


_PLACEHOLDER_RE = re.compile(r"%\(\w+\)s")


def _shield_format_placeholders(text: str) -> tuple[str, list[str]]:
    """Keep gettext %(name)s and %% safe from machine translation."""
    parts: list[str] = []

    def _sub(m: re.Match[str]) -> str:
        parts.append(m.group(0))
        return f"ZZZ{len(parts) - 1}ZZZ"

    shielded = _PLACEHOLDER_RE.sub(_sub, text)
    shielded = shielded.replace("%%", "ZZZPCTZZZ")
    return shielded, parts


def _unshield_format_placeholders(text: str, parts: list[str]) -> str:
    out = text
    for i, p in enumerate(parts):
        out = out.replace(f"ZZZ{i}ZZZ", p)
    return out.replace("ZZZPCTZZZ", "%%")


def _translate_text(text: str, target: str) -> str:
    from deep_translator import GoogleTranslator

    shielded, parts = _shield_format_placeholders(text)

    def _call(src: str) -> str:
        return GoogleTranslator(source="en", target=target).translate(src)

    if len(shielded) <= 4900 or parts:
        return _unshield_format_placeholders(_call(shielded), parts)

    chunks: list[str] = []
    chunk = 4000
    for i in range(0, len(shielded), chunk):
        segment = shielded[i : i + chunk]
        chunks.append(_call(segment))
        time.sleep(0.15)
    return _unshield_format_placeholders("".join(chunks), parts)


# Batch translate is fast but occasionally returns English for every string (seen with zh-CN, ro).
SEQUENTIAL_TARGETS = frozenset({"zh-CN", "ro"})


def _translate_msgids_batch(
    msgids: list[str],
    target: str,
    *,
    sequential: bool = False,
    progress=None,
) -> list[str]:
    """Translate msgids; use one HTTP call per string for fragile target languages."""
    from deep_translator import GoogleTranslator

    translator = GoogleTranslator(source="en", target=target, timeout=35)
    shielded_info = [_shield_format_placeholders(m) for m in msgids]
    shielded = [s for s, _ in shielded_info]
    parts_list = [p for _, p in shielded_info]

    use_serial = sequential or target in SEQUENTIAL_TARGETS
    out: list[str] = []

    if use_serial:
        for i, (sh, parts) in enumerate(shielded_info):
            try:
                tr = translator.translate(sh)
                out.append(_unshield_format_placeholders(tr, parts))
            except Exception:
                out.append(msgids[i])
            time.sleep(0.06)
            if progress and (i + 1) % 40 == 0:
                progress(f"  … {i + 1}/{len(msgids)}")
        return out

    batch_size = 25
    for start in range(0, len(shielded), batch_size):
        batch = shielded[start : start + batch_size]
        batch_parts = parts_list[start : start + batch_size]
        batch_msgids = msgids[start : start + batch_size]
        try:
            translated = translator.translate_batch(batch)
        except Exception:
            translated = None
        if not translated or len(translated) != len(batch):
            translated = []
            for k in range(len(batch)):
                ii = start + k
                try:
                    translated.append(translator.translate(shielded[ii]))
                    time.sleep(0.05)
                except Exception:
                    translated.append(shielded[ii])
        for j, tr in enumerate(translated):
            unsh = _unshield_format_placeholders(tr, batch_parts[j])
            if unsh == batch_msgids[j] and len(batch_msgids[j]) > 3:
                try:
                    tr2 = translator.translate(batch[j])
                    unsh = _unshield_format_placeholders(tr2, batch_parts[j])
                except Exception:
                    pass
            out.append(unsh)
        time.sleep(0.12)
        if progress:
            progress(f"  … {min(start + batch_size, len(msgids))}/{len(msgids)}")
    return out


class Command(BaseCommand):
    help = "Generate django.po / django.mo for all LANGUAGES except English."

    def add_arguments(self, parser):
        parser.add_argument(
            "--translate",
            action="store_true",
            help="Fill msgstr via Google Translate (network). Without it, msgstr copies msgid (English).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report msgid count; do not write files.",
        )
        parser.add_argument(
            "--only",
            default="",
            help="Comma-separated Django language codes to build (default: all except en).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Translate at most this many msgids (0 = all). For smoke tests.",
        )
        parser.add_argument(
            "--sequential",
            action="store_true",
            help="One request per string (slower, more reliable than batch).",
        )

    def handle(self, *args, **options):
        translate: bool = options["translate"]
        dry: bool = options["dry_run"]
        only_raw: str = options["only"]
        only_set = {x.strip() for x in only_raw.split(",") if x.strip()} if only_raw else None
        limit: int = options["limit"]
        sequential_flag: bool = options["sequential"]

        if translate:
            try:
                import deep_translator  # noqa: F401
            except ImportError as e:
                raise CommandError(
                    "deep-translator is required for --translate. "
                    "Install dependencies: pip install deep-translator polib"
                ) from e

        msgids = collect_all_msgids()
        if limit > 0:
            msgids = msgids[:limit]
        self.stdout.write(self.style.NOTICE(f"Collected {len(msgids)} msgids"))

        if dry:
            return

        base: Path = settings.BASE_DIR

        for code, _name in settings.LANGUAGES:
            if code == "en":
                continue
            if only_set is not None and code not in only_set:
                continue
            self.stdout.write(self.style.NOTICE(f"Building {code} ({len(msgids)} strings)..."))
            locale = to_locale(code)
            target_dir = base / "locale" / locale / "LC_MESSAGES"
            target_dir.mkdir(parents=True, exist_ok=True)
            po_path = target_dir / "django.po"
            mo_path = target_dir / "django.mo"

            po = polib.POFile()
            po.metadata = {
                "Project-Id-Version": "WMCSP 1.0",
                "Report-Msgid-Bugs-To": "",
                "POT-Creation-Date": "",
                "PO-Revision-Date": "",
                "Last-Translator": "",
                "Language-Team": "",
                "Language": locale.replace("_", "-"),
                "MIME-Version": "1.0",
                "Content-Type": "text/plain; charset=utf-8",
                "Content-Transfer-Encoding": "8bit",
                "Plural-Forms": PLURAL_FORMS.get(code, PLURAL_FORMS["en"]),
            }

            gt_target = GOOGLE_TARGET_BY_DJANGO_LANG.get(code)
            if translate and not gt_target:
                raise CommandError(f"No Google Translate target mapped for language {code!r}")

            if translate and gt_target:
                try:
                    translated_list = _translate_msgids_batch(
                        msgids,
                        gt_target,
                        sequential=sequential_flag,
                        progress=lambda m: self.stdout.write(m),
                    )
                except Exception as exc:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[{code}] batch translate failed ({exc!s}); falling back to English msgstr"
                        )
                    )
                    translated_list = list(msgids)
                for msgid, msgstr in zip(msgids, translated_list, strict=True):
                    po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
            else:
                for msgid in msgids:
                    po.append(polib.POEntry(msgid=msgid, msgstr=msgid))

            po.save(po_path)
            po.save_as_mofile(str(mo_path))
            self.stdout.write(self.style.SUCCESS(f"Wrote {po_path} ({len(po)} entries)"))
