from frappe.tests.utils import FrappeTestCase

from goldora.remarks import strip_reference_line


class TestStripReferenceLine(FrappeTestCase):
	"""The remark is frozen in the creating user's language, so both the English
	source string and its Arabic translation must be stripped regardless of the
	language the report is being read in."""

	def test_strips_english(self):
		self.assertEqual(strip_reference_line("Reference #no dated 2026-08-09"), "")

	def test_strips_arabic(self):
		self.assertEqual(strip_reference_line("المرجع # no بتاريخ 2026-08-09"), "")

	def test_strips_payment_entry_template(self):
		self.assertEqual(strip_reference_line("Transaction reference no 123 dated 2026-08-09"), "")

	def test_keeps_the_actual_note(self):
		self.assertEqual(strip_reference_line("المرجع # no بتاريخ 2026-08-09\nراتب شهر 6"), "راتب شهر 6")
		self.assertEqual(strip_reference_line("عهدة مبارك"), "عهدة مبارك")

	def test_strips_when_glued_to_the_note(self):
		"""GL Entry joins user_remark and remark with a newline, but rows exist
		where that newline is gone and the boilerplate runs straight on from the
		note — the shape the client reported from the printed statement."""
		self.assertEqual(strip_reference_line("مستحقات عذبهالمرجع # no بتاريخ 10-08-2026"), "مستحقات عذبه")

	def test_empty_input(self):
		self.assertIsNone(strip_reference_line(None))
		self.assertEqual(strip_reference_line(""), "")
