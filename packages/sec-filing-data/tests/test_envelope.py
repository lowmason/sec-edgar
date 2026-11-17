import unittest
from pathlib import Path

from sec_filing_data.envelope import (
    Document,
    EnvelopeError,
    Party,
    Submission,
    document_text,
    parse_submission,
)

FIXTURE = Path(__file__).parent / "fixtures" / "submission-13f.txt"
FORM4_FIXTURE = Path(__file__).parent / "fixtures" / "submission-form4.txt"

PRIMARY_TEXT = (
    b"<XML>\n"
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<edgarSubmission xmlns="http://www.sec.gov/edgar/thirteenffiler">\n'
    b"  <formData><tableEntryTotal>1</tableEntryTotal></formData>\n"
    b"</edgarSubmission>\n"
    b"</XML>\n"
)
INFOTABLE_TEXT = (
    b"<XML>\n"
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">\n'
    b"  <infoTable><nameOfIssuer>EXAMPLE CORP</nameOfIssuer></infoTable>\n"
    b"  </TEXT> not at line start\n"
    b"</informationTable>\n"
    b"</XML>\n"
)


def build_submission(header: str = "", documents: tuple[str, ...] = ()) -> bytes:
    """A submission whose header holds `header` and whose body holds `documents` as given."""
    return (
        "<SEC-DOCUMENT>x.txt : 20260101\n"
        "<SEC-HEADER>x.hdr.sgml : 20260101\n"
        f"{header}"
        "</SEC-HEADER>\n"
        f"{''.join(documents)}"
        "</SEC-DOCUMENT>\n"
    ).encode()


def build_document(
    text: str = "body\n", *, type_line: str = "<TYPE>8-K\n", extra: str = ""
) -> str:
    return f"<DOCUMENT>\n{type_line}{extra}<TEXT>\n{text}</TEXT>\n</DOCUMENT>\n"


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_bytes()
        self.submission = parse_submission(self.raw)

    def test_header_fields_and_acceptance(self):
        self.assertEqual(
            self.submission.fields,
            (
                ("ACCESSION NUMBER", "0001000097-26-000006"),
                ("CONFORMED SUBMISSION TYPE", "13F-HR"),
                ("PUBLIC DOCUMENT COUNT", "2"),
                ("CONFORMED PERIOD OF REPORT", "20260630"),
                ("FILED AS OF DATE", "20260814"),
                ("DATE AS OF CHANGE", "20260814"),
            ),
        )
        self.assertEqual(self.submission.field("CONFORMED SUBMISSION TYPE"), "13F-HR")
        self.assertIsNone(self.submission.field("FORM TYPE"))
        self.assertEqual(self.submission.acceptance_datetime, "20260814160523")

    def test_private_to_public_tag(self):
        self.assertFalse(self.submission.private_to_public)

        tagged = self.raw.replace(
            b"<ACCEPTANCE-DATETIME>20260814160523\n",
            b"<ACCEPTANCE-DATETIME>20260814160523\n<PRIVATE-TO-PUBLIC>\n",
        )
        self.assertNotEqual(tagged, self.raw)
        self.assertTrue(parse_submission(tagged).private_to_public)

    def test_parties(self):
        self.assertEqual(
            self.submission.parties,
            (
                Party(
                    role="FILER",
                    name="KINGDON CAPITAL MANAGEMENT, L.L.C.",
                    cik="0001000097",
                ),
            ),
        )

    def test_document_list_and_offsets(self):
        documents = self.submission.documents
        self.assertEqual(
            [(d.type, d.sequence, d.filename, d.description) for d in documents],
            [
                ("13F-HR", 1, "primary_doc.xml", None),
                ("INFORMATION TABLE", 2, "infotable.xml", "FORM 13F INFORMATION TABLE"),
            ],
        )
        for doc, expected in zip(documents, (PRIMARY_TEXT, INFOTABLE_TEXT)):
            self.assertEqual(
                self.raw[doc.text_offset : doc.text_offset + doc.text_length], expected
            )
            self.assertEqual(
                self.raw[doc.text_offset - len(b"<TEXT>\n") : doc.text_offset],
                b"<TEXT>\n",
            )
            self.assertTrue(
                self.raw[doc.text_offset + doc.text_length :].startswith(b"</TEXT>\n")
            )

    def test_document_text_strips_xml_wrapper(self):
        primary, information_table = self.submission.documents
        text = document_text(self.raw, primary)
        self.assertTrue(text.startswith(b"<?xml"))
        self.assertTrue(text.endswith(b"</edgarSubmission>"))
        self.assertNotIn(b"<XML>", text)
        self.assertNotIn(b"</XML>", text)

        table = document_text(self.raw, information_table)
        self.assertTrue(table.startswith(b"<?xml"))
        self.assertTrue(table.endswith(b"</informationTable>"))

    def test_closing_tag_must_start_a_line(self):
        information_table = self.submission.documents[1]
        text = self.raw[information_table.text_offset :][
            : information_table.text_length
        ]
        self.assertIn(b"\n  </TEXT> not at line start\n", text)
        self.assertIn(b"</informationTable>", text)

    def test_missing_header_raises(self):
        start = self.raw.index(b"<SEC-HEADER>")
        end = self.raw.index(b"</SEC-HEADER>\n") + len(b"</SEC-HEADER>\n")
        with self.assertRaises(EnvelopeError):
            parse_submission(self.raw[:start] + self.raw[end:])

    def test_non_utf8_header_bytes(self):
        raw = self.raw.replace(b"KINGDON", b"KINGD\xe9N")
        self.assertNotEqual(raw, self.raw)
        submission = parse_submission(raw)
        self.assertIn("�", submission.parties[0].name)
        self.assertEqual(submission.parties[0].cik, "0001000097")

    def test_crlf_line_endings(self):
        raw = self.raw.replace(b"\n", b"\r\n")
        submission = parse_submission(raw)
        self.assertEqual(submission.fields, self.submission.fields)
        self.assertEqual(submission.acceptance_datetime, "20260814160523")
        self.assertEqual(submission.parties, self.submission.parties)
        self.assertEqual(
            [
                (d.type, d.sequence, d.filename, d.description)
                for d in submission.documents
            ],
            [
                (d.type, d.sequence, d.filename, d.description)
                for d in self.submission.documents
            ],
        )
        for doc, expected in zip(submission.documents, (PRIMARY_TEXT, INFOTABLE_TEXT)):
            self.assertEqual(
                raw[doc.text_offset : doc.text_offset + doc.text_length],
                expected.replace(b"\n", b"\r\n"),
            )
        self.assertTrue(
            document_text(raw, submission.documents[0]).startswith(b"<?xml")
        )


class HeaderTests(unittest.TestCase):
    def test_field_returns_first_value(self):
        raw = build_submission(
            "ITEM INFORMATION:\t\tResults of Operations\n"
            "ITEM INFORMATION:\t\tFinancial Statements\n"
        )
        submission = parse_submission(raw)
        self.assertEqual(
            submission.fields,
            (
                ("ITEM INFORMATION", "Results of Operations"),
                ("ITEM INFORMATION", "Financial Statements"),
            ),
        )
        self.assertEqual(submission.field("ITEM INFORMATION"), "Results of Operations")

    def test_form_4_parties(self):
        header = (
            "ACCESSION NUMBER:\t\t0000000001-26-000001\n"
            "\n"
            "ISSUER:\t\n"
            "\n"
            "\tCOMPANY DATA:\t\n"
            "\t\tCOMPANY CONFORMED NAME:\t\t\tACME CORP\n"
            "\t\tCENTRAL INDEX KEY:\t\t\t0000001234\n"
            "\n"
            "REPORTING-OWNER:\t\n"
            "\n"
            "\tOWNER DATA:\t\n"
            "\t\tCOMPANY CONFORMED NAME:\t\t\tDOE JANE\n"
            "\t\tCENTRAL INDEX KEY:\t\t\t0000005678\n"
            "\n"
            "\tFORMER COMPANY:\t\n"
            "\t\tFORMER CONFORMED NAME:\t\tROE JANE\n"
            "\n"
            "REPORTING-OWNER:\t\n"
            "\n"
            "\tOWNER DATA:\t\n"
            "\t\tCOMPANY CONFORMED NAME:\t\t\tDOE JOHN\n"
            "\t\tCENTRAL INDEX KEY:\t\t\t0000009999\n"
        )
        submission = parse_submission(build_submission(header))
        self.assertEqual(
            submission.parties,
            (
                Party(role="ISSUER", name="ACME CORP", cik="0000001234"),
                Party(role="REPORTING-OWNER", name="DOE JANE", cik="0000005678"),
                Party(role="REPORTING-OWNER", name="DOE JOHN", cik="0000009999"),
            ),
        )
        self.assertEqual(
            submission.fields, (("ACCESSION NUMBER", "0000000001-26-000001"),)
        )

    def test_party_without_name_or_cik(self):
        submission = parse_submission(
            build_submission("FILER:\t\n\n\tFILING VALUES:\t\n\t\tFORM TYPE:\t\t8-K\n")
        )
        self.assertEqual(
            submission.parties, (Party(role="FILER", name=None, cik=None),)
        )
        self.assertEqual(submission.fields, ())

    def test_party_ends_at_next_top_level_line(self):
        header = (
            "FILER:\t\n"
            "\tCOMPANY DATA:\t\n"
            "\t\tCOMPANY CONFORMED NAME:\t\t\tFIRST CO\n"
            "SROS:\t\tNYSE\n"
            "\t\tCENTRAL INDEX KEY:\t\t\t0000000042\n"
            "SUBJECT COMPANY:\t\n"
            "\t\tCOMPANY CONFORMED NAME:\t\t\tSECOND CO\n"
            "\t\tCOMPANY CONFORMED NAME:\t\t\tNOT THE FIRST\n"
        )
        submission = parse_submission(build_submission(header))
        self.assertEqual(
            submission.parties,
            (
                Party(role="FILER", name="FIRST CO", cik=None),
                Party(role="SUBJECT COMPANY", name="SECOND CO", cik=None),
            ),
        )
        self.assertEqual(submission.fields, (("SROS", "NYSE"),))

    def test_acceptance_datetime_absent(self):
        submission = parse_submission(build_submission("ACCESSION NUMBER:\t\t1\n"))
        self.assertIsNone(submission.acceptance_datetime)
        self.assertFalse(submission.private_to_public)

    def test_header_tag_at_start_of_file(self):
        raw = b"<SEC-HEADER>\nACCESSION NUMBER:\t\t1\n</SEC-HEADER>\n"
        self.assertEqual(parse_submission(raw).fields, (("ACCESSION NUMBER", "1"),))

    def test_unterminated_header_raises(self):
        raw = b"<SEC-DOCUMENT>x.txt\n<SEC-HEADER>\nACCESSION NUMBER:\t\t1\n"
        with self.assertRaises(EnvelopeError):
            parse_submission(raw)

    def test_empty_input_raises(self):
        with self.assertRaises(EnvelopeError):
            parse_submission(b"")

    def test_error_is_a_value_error(self):
        self.assertTrue(issubclass(EnvelopeError, ValueError))


class DocumentTests(unittest.TestCase):
    def test_no_documents(self):
        self.assertEqual(
            parse_submission(build_submission("ACCESSION NUMBER:\t\t1\n")).documents, ()
        )

    def test_optional_values_and_sequence(self):
        raw = build_submission(
            documents=(
                build_document(
                    extra="<SEQUENCE>x\n<FILENAME>a.htm\n<DESCRIPTION>  Annual report  \n"
                ),
                build_document(type_line=""),
                build_document(extra="<SEQUENCE>12\n"),
            )
        )
        first, second, third = parse_submission(raw).documents
        self.assertEqual(
            (first.type, first.sequence, first.filename, first.description),
            ("8-K", None, "a.htm", "Annual report"),
        )
        self.assertEqual(
            (second.type, second.sequence, second.filename, second.description),
            ("", None, None, None),
        )
        self.assertEqual(third.sequence, 12)

    def test_document_without_text_start_raises(self):
        raw = build_submission(documents=("<DOCUMENT>\n<TYPE>8-K\n</DOCUMENT>\n",))
        with self.assertRaises(EnvelopeError):
            parse_submission(raw)

    def test_document_without_text_end_raises(self):
        raw = build_submission(
            documents=("<DOCUMENT>\n<TYPE>8-K\n<TEXT>\nbody\n</DOCUMENT>\n",)
        )
        with self.assertRaises(EnvelopeError):
            parse_submission(raw)

    def test_text_end_beyond_the_document_raises(self):
        raw = build_submission(
            documents=(
                "<DOCUMENT>\n<TYPE>8-K\n<TEXT>\nbody\n</DOCUMENT>\n",
                build_document(),
            )
        )
        with self.assertRaises(EnvelopeError):
            parse_submission(raw)

    def test_document_without_end_raises(self):
        raw = build_submission(
            documents=("<DOCUMENT>\n<TYPE>8-K\n<TEXT>\nbody\n</TEXT>\n",)
        )
        with self.assertRaises(EnvelopeError):
            parse_submission(raw)

    def test_empty_text(self):
        raw = build_submission(documents=(build_document(""),))
        (doc,) = parse_submission(raw).documents
        self.assertEqual(doc.text_length, 0)
        self.assertEqual(document_text(raw, doc), b"")

    def test_indented_document_tag_does_not_start_a_document(self):
        raw = build_submission(
            documents=(build_document("  <DOCUMENT>\n  </DOCUMENT>\n"),)
        )
        (doc,) = parse_submission(raw).documents
        self.assertEqual(
            raw[doc.text_offset : doc.text_offset + doc.text_length],
            b"  <DOCUMENT>\n  </DOCUMENT>\n",
        )


class DocumentTextTests(unittest.TestCase):
    def text_of(self, text: str) -> bytes:
        raw = build_submission(documents=(build_document(text),))
        (doc,) = parse_submission(raw).documents
        return document_text(raw, doc)

    def test_xbrl_wrapper_is_removed(self):
        self.assertEqual(
            self.text_of("<XBRL>\n<?xml version='1.0'?>\n<root/>\n</XBRL>\n"),
            b"<?xml version='1.0'?>\n<root/>",
        )

    def test_wrapper_tag_case_is_ignored(self):
        self.assertEqual(self.text_of("<xml>\n<a/>\n</XML>\n"), b"<a/>")
        self.assertEqual(self.text_of("<Xbrl><a/></xbrl>\n"), b"<a/>")

    def test_text_without_wrapper_is_only_stripped(self):
        self.assertEqual(
            self.text_of("\n  <html>body</html>  \n\n"), b"<html>body</html>"
        )

    def test_mismatched_wrapper_is_kept(self):
        self.assertEqual(
            self.text_of("<XML>\n<a/>\n</XBRL>\n"), b"<XML>\n<a/>\n</XBRL>"
        )

    def test_only_one_wrapper_is_removed(self):
        self.assertEqual(
            self.text_of("<XML>\n<XBRL>\n<a/>\n</XBRL>\n</XML>\n"),
            b"<XBRL>\n<a/>\n</XBRL>",
        )

    def test_wrapper_tags_alone(self):
        self.assertEqual(self.text_of("<XML></XML>\n"), b"")

    def test_open_tag_only_is_kept(self):
        self.assertEqual(self.text_of("<XML>\n<a/>\n"), b"<XML>\n<a/>")

    def test_offsets_come_from_the_document(self):
        doc = Document(
            sequence=1,
            type="X",
            filename=None,
            description=None,
            text_offset=3,
            text_length=5,
        )
        self.assertEqual(document_text(b"abc<a/>def", doc), b"<a/>d")


class RealSubmissionTests(unittest.TestCase):
    """A pilot Form 4 as the SEC filed it: public data, so its names and values stay as filed."""

    def test_real_form4_header(self):
        raw = FORM4_FIXTURE.read_bytes()
        submission = parse_submission(raw)

        self.assertEqual(submission.field("CONFORMED SUBMISSION TYPE"), "4")
        self.assertEqual(submission.acceptance_datetime, "20260702172241")
        self.assertIn(
            Party(role="REPORTING-OWNER", name="HUSTON BENJAMIN E.", cik="0001700537"),
            submission.parties,
        )
        self.assertIn(
            Party(role="ISSUER", name="CARVANA CO.", cik="0001690820"),
            submission.parties,
        )

        (document,) = submission.documents
        self.assertEqual(document.type, "4")
        self.assertEqual(document.filename, "wk-form4_1783027358.xml")
        self.assertTrue(document_text(raw, document).startswith(b"<?xml"))


class SubmissionTests(unittest.TestCase):
    def test_submission_is_frozen(self):
        submission = Submission(
            fields=(("A", "1"),),
            acceptance_datetime=None,
            private_to_public=False,
            parties=(),
            documents=(),
        )
        with self.assertRaises(AttributeError):
            submission.fields = ()
        self.assertEqual(submission.field("A"), "1")
        self.assertIsNone(submission.field("B"))


if __name__ == "__main__":
    unittest.main()
