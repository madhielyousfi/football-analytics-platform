"""Generate a VAPID keypair for Web Push (run once, store in .env).

Usage:  python scripts/gen_vapid.py
Needs:  pip install ecdsa
"""

from base64 import urlsafe_b64encode

from ecdsa import NIST256p, SigningKey


def main() -> None:
    private = SigningKey.generate(curve=NIST256p)
    public = private.get_verifying_key()
    raw_private = private.to_string()
    raw_public = b"\x04" + public.to_string()
    print("Add to .env (and GitHub secret VAPID_* for the poller):")
    print(f"VAPID_PUBLIC_KEY={urlsafe_b64encode(raw_public).decode().rstrip('=')}")
    print(f"VAPID_PRIVATE_KEY={urlsafe_b64encode(raw_private).decode().rstrip('=')}")
    print('VAPID_SUBJECT=mailto:you@example.com')


if __name__ == "__main__":
    main()
