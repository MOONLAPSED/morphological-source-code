import io, hashlib, hmac


if __name__ == '__main__':
    with open(hashlib.__file__, "rb") as f:

        digest = hashlib.file_digest(f, "sha256")


    digest.hexdigest()

    buf = io.BytesIO(b"somedata")

    mac1 = hmac.HMAC(b"key", digestmod=hashlib.sha512)

    digest = hashlib.file_digest(buf, lambda: mac1)

    digest is mac1

    mac2 = hmac.HMAC(b"key", b"somedata", digestmod=hashlib.sha512)
    # This part correctly demonstrates determinism: two HMAC calculations 
    # with the same key, data (`b"somedata"`), and hashing algorithm
    # (SHA512) will produce identical hashes.
    mac3 = mac1.digest() == mac2.digest()
    print(mac3)
