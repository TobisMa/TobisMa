from string import ascii_letters, digits

class CodeString(str):
    def __init__(self, value):
        str.__init__(self)
        self.value = value

    def contains(self, other: str, in_string=None, func=False, lower=False) -> bool:
        if lower:
            self.value = self.value.lower()
        quoted = False
        for i in range(len(other) - 1, len(self.value)):
            if quoted and in_string == False:
                continue
            elif not quoted and in_string == True:
                continue
            elif i - len(other) < int(quoted) and quoted:
                continue

            if self.value[i] in ("\"", "\'"):
                quoted = i if quoted else False
                continue

            if other == self.value[i - len(other) + 1:i + 1]:
                if func:
                    if (" " + self.value)[
                        i - len(other) + 1
                    ] not in ascii_letters and (self.value + " ")[i + 1] not in (
                        ascii_letters + digits
                    ):
                        return True
                else:
                    return True

        return False

    def __str__(self) -> str:
        return self.value
