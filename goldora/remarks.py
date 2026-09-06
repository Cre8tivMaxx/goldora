"""Stripping ERPNext's auto-generated reference boilerplate out of remarks.

Both Journal Entry (`create_remarks`) and Payment Entry (`set_remarks`) prepend a
machine-written reference line to the remark the user actually typed. The client
wants only their own note in the General Ledger and the Bank Statement.

The line is generated at document-write time in the *writing* user's language and
then frozen, so a remark written in an Arabic session never matches an English
session's pattern. This site is English + Arabic, so we match both.
"""

import re

from frappe.translate import get_all_translations
from frappe.utils.caching import request_cache

# {0} = reference no, {1} = reference date
REFERENCE_TEMPLATES = (
	# Journal Entry
	"Reference #{0} dated {1}",
	# Payment Entry
	"Transaction reference no {0} dated {1}",
)

LANGUAGES = ("en", "ar")


@request_cache
def _variants():
	variants = set()
	for template in REFERENCE_TEMPLATES:
		variants.add(template)
		for lang in LANGUAGES:
			variants.add(get_all_translations(lang).get(template, template))
	return variants


def reference_prefixes():
	"""The literal text each variant starts with, e.g. 'Reference #', 'المرجع # '.

	Used to narrow a scan to rows that could possibly contain the boilerplate.
	A variant starting with the placeholder has no usable prefix and is skipped;
	an empty result means the caller must not narrow at all."""
	return sorted({prefix for v in _variants() if (prefix := v.split("{0}")[0].strip())})


@request_cache
def _reference_patterns():
	variants = _variants()

	return [
		re.compile(
			# Deliberately not anchored at the start: the reference text is not
			# always on its own line. GL Entry joins user_remark and remark with a
			# newline, but rows exist where that newline was lost and the boilerplate
			# is glued onto the end of the user's note
			# ("مستحقات عذبهالمرجع # no بتاريخ 10-08-2026"). Matching from the phrase
			# to end-of-line strips it in both shapes.
			re.escape(v).replace(r"\{0\}", ".*?").replace(r"\{1\}", ".*?") + r"\s*$",
			re.MULTILINE,
		)
		for v in variants
	]


def strip_reference_line(remarks):
	"""Return `remarks` without the auto-generated reference text.

	Safe on None/empty. Drops any line left blank by the removal."""
	if not remarks:
		return remarks

	for pattern in _reference_patterns():
		remarks = pattern.sub("", remarks)

	return "\n".join(line for line in remarks.splitlines() if line.strip())


def drop_reference_remark(doc, method=None):
	"""doc_events validate hook for Journal Entry and Payment Entry.

	Runs after the controller's own validate, which is what (re)builds the remark
	on every save, so stripping here is not undone."""
	# both doctypes let the user opt out of the generated remark entirely
	if doc.get("custom_remark") or doc.get("custom_remarks"):
		return

	for fieldname in ("remark", "remarks"):
		if doc.meta.has_field(fieldname):
			doc.set(fieldname, strip_reference_line(doc.get(fieldname)))
