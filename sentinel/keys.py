"""Demo cryptographic keys and signing/verification for AgentTrust.

Uses HMAC-SHA256 as a simplified JWS scheme for the demo. This is real
cryptographic verification (not a string comparison) — the only
simplification vs full A2A v1.0 JWS is using a symmetric key (HMAC)
instead of asymmetric (ECDSA P-256). The JWS envelope structure
(protected header + payload + signature) is the same.

In production A2A v1.0, agent cards are signed with ES256 (ECDSA P-256)
per RFC 7515. This demo simulates that flow with HMAC-SHA256 using a
shared secret key, which is sufficient to demonstrate:
  - Legitimate agents can produce valid signatures
  - Forged/tampered signatures are rejected
  - Missing signatures are rejected
"""

import base64
import hashlib
import hmac
import json

# ---------------------------------------------------------------
# Demo secret key — in production this would be a private key held
# by each agent and the corresponding public key published for
# verification. For the demo, we use a shared HMAC secret.
# ---------------------------------------------------------------
DEMO_SECRET_KEY = b"a2a-sentinel-demo-secret-key-2026"


def _base64url_encode(data: bytes) -> str:
    """Base64url encode without padding (per RFC 7515 / JWS spec)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(s: str) -> bytes:
    """Base64url decode, adding padding back as needed."""
    # Add padding
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def make_protected_header() -> str:
    """Create the base64url-encoded JWS protected header.

    Returns the header indicating HMAC-SHA256 algorithm, matching the
    JWS structure that A2A v1.0 uses for agent card signatures.
    """
    header = json.dumps({"alg": "HS256"}, separators=(",", ":"), sort_keys=True)
    return _base64url_encode(header.encode("utf-8"))


def card_dict_to_signing_payload(card_dict: dict) -> str:
    """Convert an AgentCard dict to a canonical signing payload.

    Removes the 'signatures' field (since signatures can't sign
    themselves), then serializes to deterministic JSON (sorted keys,
    no extra whitespace) — matching RFC 8785 canonicalization that
    the A2A spec recommends.
    """
    # Copy without signatures
    payload_dict = {k: v for k, v in card_dict.items() if k != "signatures"}
    canonical = json.dumps(payload_dict, separators=(",", ":"), sort_keys=True)
    return _base64url_encode(canonical.encode("utf-8"))


def compute_signature(protected: str, payload_b64: str) -> str:
    """Compute HMAC-SHA256 signature over the JWS signing input.

    JWS signing input = protected + "." + payload (both base64url-encoded).
    Returns the base64url-encoded signature.
    """
    signing_input = f"{protected}.{payload_b64}".encode("ascii")
    sig = hmac.new(DEMO_SECRET_KEY, signing_input, hashlib.sha256).digest()
    return _base64url_encode(sig)


def verify_signature(protected: str, payload_b64: str, signature: str) -> bool:
    """Verify a JWS HMAC-SHA256 signature.

    Returns True if the signature is valid, False otherwise.
    """
    expected = compute_signature(protected, payload_b64)
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected, signature)


def sign_card_dict(card_dict: dict) -> dict:
    """Sign an AgentCard dict and return a new dict with the signature added.

    This is what a legitimate agent calls before presenting its card.
    The returned dict has a 'signatures' field with one valid JWS entry.
    """
    protected = make_protected_header()
    payload_b64 = card_dict_to_signing_payload(card_dict)
    signature = compute_signature(protected, payload_b64)

    signed_dict = dict(card_dict)
    signed_dict["signatures"] = [
        {
            "protected": protected,
            "signature": signature,
        }
    ]
    return signed_dict
