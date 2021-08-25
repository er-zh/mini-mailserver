# Eric Zheng
# onyen: erzh
# PID: 730294463

class MailParser():
    def __init__(self):
        self.status = 0 # any non-zero value represents parse failure
        self.bad_token = ''
        self.remainder = ''

        self._stream = '' # holds remaining unparsed portion of the input string
        self._invalid_chars = {' ', '\t', '<', '>', '(', ')', '[', ']', '\\', '.', ',', ';', ':', '@', '"'}

    def parse(self, inputstr):
        self._stream = inputstr
        self.bad_token = ''
        self.status = 0

        self._parse_mail_from_cmd()

    def _parse_mail_from_cmd(self):
        # <mail-from-cmd> --> MAIL<whitespace>FROM:<nullspace><reverse-path><nullspace><CRLF>
        try:
            assert self._stream[:4] == 'MAIL'
            self._shift(4)

            self._parse_whitespace()

            assert self._stream[:5] == 'FROM:'
            self._shift(5)

            self._parse_nullspace()

            self._parse_path()

            self._parse_nullspace()

            assert self._stream[0] == '\n'
        except (AssertionError, IndexError):
            self._fail_parse('mail-from-cmd')
            return

    def _parse_whitespace(self): # handles checking for <SP> as well
        # <whitespace> --> <SP>(<null>|<whitespace>)
        try:
            assert self._stream[0] == ' ' or self._stream[0] == '\t'
            self._shift()

            # iteratively check for recursing <whitespace> rule
            while self._stream[0] == ' ' or self._stream[0] == '\t':
                self._shift()
        except (AssertionError, IndexError):
            self._fail_parse('whitespace')
            return

    def _parse_nullspace(self):
        # <nullspace> --> <null>|<whitespace>
        # iteratively check for recursing <whitespace> rule
        if self._stream[0] == ' ' or self._stream[0] == '\t':
            self._parse_whitespace()

    def _parse_path(self):
        # <path> --> <<mailbox>>
        # <reverse-path> prod rule seems like an alias for <path> so this handles both rules
        try:
            assert self._stream[0] == '<'
            self._shift()

            self._parse_mailbox()

            assert self._stream[0] == '>'
            self._shift()
        except (AssertionError, IndexError):
            self._fail_parse('path')
            return

    def _parse_mailbox(self):
        # <mailbox> --> <local-part>@<domain>
        try:
            self._parse_string()

            assert self._stream[0] == '@'
            self._shift()

            self._parse_domain()
        except (AssertionError, IndexError):
            self._fail_parse('mailbox')
            return

    def _parse_string(self):
        # <string> --> <char>(<null>|<string>)
        # <local-part> production rule seems to just be an alias for <string> so this handles both
        try:
            assert self._stream[0] not in self._invalid_chars
            self._shift()

            # TODO are newlines allowed?
            while self._stream[0] not in self._invalid_chars:
                self._shift()
        except (AssertionError, IndexError):
            self._fail_parse('string')
            return

    def _parse_domain(self):
        # <domain> --> <element>(<null>|.<domain>)
        self._parse_element()

        try:
            if self._stream[0] == '.':
                self._shift()
                self._parse_domain()
        except IndexError:
            pass

    def _parse_element(self):
        # <element> --> <letter>(<null>|<let-dig-str>)
        # substituted in <name> prod and left factored

        try:
            assert self._stream[0].isalpha()
            self._shift()

            if len(self._stream) != 0 and self._stream[0].isalnum():
                self._parse_let_dig_str()
        except (AssertionError, IndexError):
            self._fail_parse('element')
            return

    def _parse_let_dig_str(self):
        # <let-dig-str> --> (<letter>|<digit>)(<null>|<let-dig-str>)
        try:
            assert self._stream[0].isalnum()
            self._shift()

            while self._stream[0].isalnum():
                self._shift()
        except (AssertionError, IndexError):
            self._fail_parse('element')
            return

    def _fail_parse(self, badtoken):
        if self.bad_token == '':
            self.bad_token = badtoken
            self.remainder = self._stream
        self.status = 1
    
    # removes the first n characters of the input string
    def _shift(self, n=1):
        self._stream = self._stream[n:]


if __name__ == "__main__":
    parser = MailParser()

    with open(0) as stdin:
        for usrinput in stdin:
            # TODO echo the user input but remove the extra newline if present
            print(usrinput[:-1] if usrinput[-1] == '\n' else usrinput)
            parser.parse(usrinput)

            if parser.status == 0:
                print('Sender ok')
            else:
                print(f'ERROR -- {parser.bad_token}')