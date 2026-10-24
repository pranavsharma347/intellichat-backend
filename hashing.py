import bcrypt


class Hash:
    @staticmethod
    def bcrypt(password: str) -> str:
        pw = password.encode("utf-8")[:72]
        return bcrypt.hashpw(pw, bcrypt.gensalt()).decode()

    @staticmethod
    def verify(hashed: str, plain: str) -> bool:
        pw = plain.encode("utf-8")[:72]
        try:
            return bcrypt.checkpw(pw, hashed.encode())
        except ValueError:
            return False