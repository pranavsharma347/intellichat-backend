import bcrypt


class Hash:
    @staticmethod
    def bcrypt(password: str) -> str:
        print("Hashing password: in Hash.bcrypt", password)
        pw = password.encode("utf-8")[:72]
        return bcrypt.hashpw(pw, bcrypt.gensalt()).decode()

    @staticmethod
    def verify(hashed: str, plain: str) -> bool:
        print("Verifying password: in Hash.verify", plain)
        pw = plain.encode("utf-8")[:72]
        try:
            return bcrypt.checkpw(pw, hashed.encode())
        except ValueError:
            return False