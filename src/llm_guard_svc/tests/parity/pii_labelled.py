"""Labelled PII test set for the native anonymize engine (LLG-04 step 3).

Because the native PII scanner is a deliberate MODEL SWAP (cc-by-nc distilbert ->
Presidio + GLiNER), it cannot be validated by golden/differential parity like the
other scanners. Instead it is gated on **entity-level recall/precision** against
this hand-annotated set (eval doc §4.4, §8.4).

Each :class:`PiiCase` carries the exact ground-truth spans over its text. Spans
are computed from a surface substring at construction (``_case``) to avoid
hand-counting offsets. All text is synthetic and deterministic — mixing
representative, adversarial, and benign (zero-PII) inputs across en + fr.

Entity types are canonical Presidio names: structured PII
(``EMAIL_ADDRESS``/``CREDIT_CARD``/``US_SSN``/``PHONE_NUMBER``/``IBAN_CODE``) from
the pattern recognizers, free-text (``PERSON``/``LOCATION``/``ORGANIZATION``) from
GLiNER.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PiiSpan:
    """One ground-truth PII entity span over a case's text."""

    start: int
    end: int
    entity: str


@dataclass(frozen=True)
class PiiCase:
    """A single labelled PII input."""

    id: str
    text: str
    lang: str  # "en" | "fr"
    spans: tuple[PiiSpan, ...]
    notes: str = ""


def _case(
    case_id: str,
    text: str,
    lang: str,
    entities: list[tuple[str, str]],
    notes: str = "",
) -> PiiCase:
    """Build a case, deriving spans from ``(entity_type, surface)`` pairs.

    Each surface must occur exactly once in ``text`` (asserted) so offsets are
    unambiguous.
    """
    spans: list[PiiSpan] = []
    for entity_type, surface in entities:
        first = text.find(surface)
        assert first != -1, f"{case_id}: surface {surface!r} not in text"
        assert (
            text.find(surface, first + 1) == -1
        ), f"{case_id}: surface {surface!r} occurs more than once; disambiguate"
        spans.append(PiiSpan(first, first + len(surface), entity_type))
    return PiiCase(case_id, text, lang, tuple(sorted(spans, key=lambda s: s.start)), notes)


PII_CASES: list[PiiCase] = [
    # ---- structured PII, English (pattern recognizers) --------------------
    _case(
        "ssn_email_en",
        "My SSN is 123-45-6789 and email bob@acme.com",
        "en",
        [("US_SSN", "123-45-6789"), ("EMAIL_ADDRESS", "bob@acme.com")],
        "Reused from corpus pii_ssn_email.",
    ),
    _case(
        "name_phone_email_en",
        "Contact Alice Johnson at +1-415-555-0132 or alice.johnson@example.org.",
        "en",
        [
            ("PERSON", "Alice Johnson"),
            ("PHONE_NUMBER", "+1-415-555-0132"),
            ("EMAIL_ADDRESS", "alice.johnson@example.org"),
        ],
        "Reused from corpus pii_name_phone_email.",
    ),
    _case(
        "credit_card_en",
        "Charge card 4111 1111 1111 1111 expiring 12/29 for the invoice.",
        "en",
        [("CREDIT_CARD", "4111 1111 1111 1111")],
        "Reused from corpus pii_credit_card; test-range card.",
    ),
    _case(
        "iban_en",
        "Please wire the deposit to IBAN GB33BUKB20201555555555 by Friday.",
        "en",
        [("IBAN_CODE", "GB33BUKB20201555555555")],
    ),
    _case(
        "ssn_only_en",
        "The applicant's social security number is 078-05-1120 on file.",
        "en",
        [("US_SSN", "078-05-1120")],
    ),
    _case(
        "email_only_en",
        "Forward the report to security-team@corp.com when ready.",
        "en",
        [("EMAIL_ADDRESS", "security-team@corp.com")],
    ),
    _case(
        "phone_uk_en",
        "Call the London office on +44 20 7946 0958 after 9am.",
        "en",
        [("PHONE_NUMBER", "+44 20 7946 0958"), ("LOCATION", "London")],
    ),
    _case(
        "card_amex_en",
        "Customer paid with Amex 3782 822463 10005 last quarter.",
        "en",
        [("CREDIT_CARD", "3782 822463 10005")],
    ),
    _case(
        "two_emails_en",
        "CC both jane@acme.io and ops@acme.io on the incident thread.",
        "en",
        [("EMAIL_ADDRESS", "jane@acme.io"), ("EMAIL_ADDRESS", "ops@acme.io")],
    ),
    # ---- free-text NER, English (GLiNER) ----------------------------------
    _case(
        "person_location_en",
        "Maria Gonzalez relocated from Seattle to Boston in March.",
        "en",
        [("PERSON", "Maria Gonzalez"), ("LOCATION", "Seattle"), ("LOCATION", "Boston")],
    ),
    _case(
        "person_org_en",
        "Dmitri Volkov joined Acme Corporation as a security analyst.",
        "en",
        [("PERSON", "Dmitri Volkov")],
        "ORGANIZATION is out of scope (not evaluated); only the PERSON is gold.",
    ),
    _case(
        "person_only_en",
        "Escalate the ticket to Priya Nair on the on-call rotation.",
        "en",
        [("PERSON", "Priya Nair")],
    ),
    _case(
        "location_only_en",
        "The data center outage affected the Frankfurt region overnight.",
        "en",
        [("LOCATION", "Frankfurt")],
    ),
    _case(
        "org_only_en",
        "We migrated the workload off Globex Industries last year.",
        "en",
        [],
        "ORGANIZATION out of scope; no PERSON/LOCATION here -> a precision case.",
    ),
    _case(
        "person_phone_en",
        "Reach Thomas O'Brien directly at (212) 555-0188 for approvals.",
        "en",
        [("PERSON", "Thomas O'Brien"), ("PHONE_NUMBER", "(212) 555-0188")],
    ),
    # ---- structured + free-text, French (en+fr requirement) ---------------
    _case(
        "name_email_fr",
        "Veuillez contacter Camille Dubois a l'adresse camille.dubois@exemple.fr.",
        "fr",
        [("PERSON", "Camille Dubois"), ("EMAIL_ADDRESS", "camille.dubois@exemple.fr")],
    ),
    _case(
        "person_location_fr",
        "Jean-Pierre Lefevre habite a Lyon depuis trois ans.",
        "fr",
        [("PERSON", "Jean-Pierre Lefevre"), ("LOCATION", "Lyon")],
    ),
    _case(
        "phone_iban_fr",
        "Appelez le +33 1 70 18 99 00 ou virez sur FR7630006000011234567890189.",
        "fr",
        [("PHONE_NUMBER", "+33 1 70 18 99 00"), ("IBAN_CODE", "FR7630006000011234567890189")],
    ),
    _case(
        "person_org_fr",
        "Sophie Marchand dirige la securite chez Entreprise Lumiere.",
        "fr",
        [("PERSON", "Sophie Marchand")],
        "ORGANIZATION is out of scope (not evaluated); only the PERSON is gold.",
    ),
    _case(
        "location_only_fr",
        "Le centre de donnees de Marseille a subi une panne cette nuit.",
        "fr",
        [("LOCATION", "Marseille")],
    ),
    _case(
        "email_only_fr",
        "Transmettez le rapport a equipe-securite@societe.fr rapidement.",
        "fr",
        [("EMAIL_ADDRESS", "equipe-securite@societe.fr")],
    ),
    # ---- adversarial ------------------------------------------------------
    _case(
        "person_looks_like_place_en",
        "Paris Hilton checked into the downtown hotel on Tuesday.",
        "en",
        [("PERSON", "Paris Hilton")],
        "Adversarial: 'Paris' is a name here, not a LOCATION.",
    ),
    _case(
        "place_looks_like_person_en",
        "Our flight to Georgia was delayed by the storm.",
        "en",
        [("LOCATION", "Georgia")],
        "Adversarial: 'Georgia' is a place here, not a PERSON.",
    ),
    _case(
        "invalid_card_en",
        "The placeholder number 1234 5678 9012 3456 is not a real card.",
        "en",
        [],
        "Adversarial negative: fails Luhn -> not a CREDIT_CARD.",
    ),
    _case(
        "version_not_ssn_en",
        "Build identifier 412-90-7781x refers to the pipeline run, not a person.",
        "en",
        [],
        "Adversarial negative: digits that should not redact as US_SSN at threshold.",
    ),
    _case(
        "email_in_url_en",
        "See the docs at https://example.com/contact for the support address.",
        "en",
        [],
        "Adversarial negative: URL contains no email address.",
    ),
    # ---- benign / zero-PII (precision floor) ------------------------------
    _case(
        "benign_pangram_en",
        "The quick brown fox jumps over the lazy dog.",
        "en",
        [],
        "Benign: no PII; any redaction is a precision failure.",
    ),
    _case(
        "benign_soc_query_en",
        "Summarize the top five firewall alert categories from last week.",
        "en",
        [],
        "Benign SOC analyst query.",
    ),
    _case(
        "benign_fr",
        "Resumez les cinq principales categories d'alertes du pare-feu.",
        "fr",
        [],
        "Benign French query.",
    ),
    _case(
        "benign_numbers_en",
        "We processed 4821 events and closed 37 cases this morning.",
        "en",
        [],
        "Benign: bare counts must not redact as structured PII.",
    ),
]
