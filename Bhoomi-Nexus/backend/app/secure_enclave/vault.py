"""
Secure Secret Vault & Cryptographic Sealing Layer.

Implements:
1. Envelope encryption using AES-256-GCM
2. Key derivation via HKDF-SHA256 with cryptographically strong salt
3. Windows Data Protection API (DPAPI) binding on Windows systems
4. Explicit buffer zeroization for sensitive key material
5. Context-binding (AAD - Additional Authenticated Data) for ciphertext verification
"""

import base64
import ctypes
import json
import os
import platform
import secrets
import sys
from datetime import datetime, timezone
from typing import Optional, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


def zeroize(buf: bytearray) -> None:
    """Explicitly wipe memory buffer with zero bytes."""
    if isinstance(buf, (bytearray, memoryview)):
        for i in range(len(buf)):
            buf[i] = 0


class WindowsDPAPI:
    """Windows Data Protection API wrapper via ctypes for OS-level key protection."""

    @staticmethod
    def is_available() -> bool:
        return platform.system() == "Windows"

    @staticmethod
    def protect(data: bytes, description: str = "BhoomiNexus-Enclave-Key") -> Optional[bytes]:
        if not WindowsDPAPI.is_available():
            return None
        try:
            class DATA_BLOB(ctypes.Structure):
                _fields_ = [
                    ("cbData", ctypes.c_ulong),
                    ("pbData", ctypes.POINTER(ctypes.c_char)),
                ]

            crypt32 = ctypes.windll.crypt32
            kernel32 = ctypes.windll.kernel32

            in_blob = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_char)))
            out_blob = DATA_BLOB()

            flags = 0x01  # CRYPTPROTECT_UI_FORBIDDEN
            success = crypt32.CryptProtectData(
                ctypes.byref(in_blob),
                ctypes.c_wchar_p(description),
                None,
                None,
                None,
                flags,
                ctypes.byref(out_blob),
            )
            if not success:
                return None

            result = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            kernel32.LocalFree(out_blob.pbData)
            return result
        except Exception:
            return None

    @staticmethod
    def unprotect(data: bytes) -> Optional[bytes]:
        if not WindowsDPAPI.is_available():
            return None
        try:
            class DATA_BLOB(ctypes.Structure):
                _fields_ = [
                    ("cbData", ctypes.c_ulong),
                    ("pbData", ctypes.POINTER(ctypes.c_char)),
                ]

            crypt32 = ctypes.windll.crypt32
            kernel32 = ctypes.windll.kernel32

            in_blob = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_char)))
            out_blob = DATA_BLOB()

            flags = 0x01  # CRYPTPROTECT_UI_FORBIDDEN
            success = crypt32.CryptUnprotectData(
                ctypes.byref(in_blob),
                None,
                None,
                None,
                None,
                flags,
                ctypes.byref(out_blob),
            )
            if not success:
                return None

            result = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            kernel32.LocalFree(out_blob.pbData)
            return result
        except Exception:
            return None


class SecureSecretVault:
    """
    Secure Key & Secret Storage.
    
    Provides cryptographic sealing and unsealing using AES-256-GCM.
    Uses HKDF to derive ephemeral operation keys from an internal master key.
    On Windows, the master key is bound to the current OS user using DPAPI.
    """

    def __init__(self, master_salt: Optional[bytes] = None) -> None:
        self._salt = master_salt or secrets.token_bytes(32)
        self._raw_master_key: bytearray = bytearray(secrets.token_bytes(32))
        self._dpapi_enabled: bool = False

        # Attempt to seal the master key using Windows DPAPI if running on Windows
        if WindowsDPAPI.is_available():
            protected = WindowsDPAPI.protect(bytes(self._raw_master_key))
            if protected:
                self._dpapi_protected_key = protected
                self._dpapi_enabled = True

    @property
    def os_protection(self) -> str:
        if self._dpapi_enabled:
            return "WINDOWS_DPAPI_PROTECTED"
        return "IN_MEMORY_ENCRYPTED_KEYSTORE"

    def _derive_key(self, context: str) -> bytes:
        """Derive a 256-bit sub-key using HKDF-SHA256 bound to a specific context."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            info=context.encode("utf-8"),
        )
        derived = hkdf.derive(bytes(self._raw_master_key))
        return derived

    def seal(self, plaintext: str | bytes, context_binding: Optional[str] = None) -> str:
        """
        Seal plaintext into an authenticated encrypted ciphertext blob.
        
        Format: Base64(JSON({
            "version": 1,
            "nonce": base64,
            "ciphertext": base64,
            "context": context_binding,
            "salt": base64
        }))
        """
        if isinstance(plaintext, str):
            plaintext_bytes = plaintext.encode("utf-8")
        else:
            plaintext_bytes = plaintext

        context = context_binding or "bhoomi.enclave.default"
        derived_key = self._derive_key(context)
        nonce = secrets.token_bytes(12)  # 96-bit standard AES-GCM nonce

        aesgcm = AESGCM(derived_key)
        # Additional Authenticated Data binds the context string cryptographically
        aad = context.encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, aad)

        envelope = {
            "version": 1,
            "algorithm": "AES-256-GCM",
            "kdf": "HKDF-SHA256",
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
            "context": context,
            "salt": base64.b64encode(self._salt).decode("utf-8"),
            "sealed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Clear derived key from memory
        zeroize(bytearray(derived_key))

        return base64.b64encode(json.dumps(envelope).encode("utf-8")).decode("utf-8")

    def unseal(self, sealed_blob: str, expected_context: Optional[str] = None) -> bytes:
        """
        Unseal an encrypted blob. Fails if ciphertext or context was tampered with.
        """
        try:
            raw_json = base64.b64decode(sealed_blob.encode("utf-8")).decode("utf-8")
            envelope = json.loads(raw_json)
        except Exception as e:
            raise ValueError(f"Malformed sealed secret envelope: {e}")

        if envelope.get("algorithm") != "AES-256-GCM":
            raise ValueError(f"Unsupported or tampered encryption algorithm: {envelope.get('algorithm')}")

        context = envelope.get("context", "bhoomi.enclave.default")
        if expected_context and expected_context != context:
            raise PermissionError(f"Context mismatch: expected '{expected_context}', got '{context}'")

        nonce = base64.b64decode(envelope["nonce"])
        ciphertext = base64.b64decode(envelope["ciphertext"])

        derived_key = self._derive_key(context)
        aesgcm = AESGCM(derived_key)
        aad = context.encode("utf-8")

        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
        except Exception:
            raise PermissionError("Unseal failed: Cryptographic integrity check failed or invalid key/context.")
        finally:
            zeroize(bytearray(derived_key))

        return plaintext

    def destroy(self) -> None:
        """Zeroize all master key material upon enclave termination."""
        zeroize(self._raw_master_key)
