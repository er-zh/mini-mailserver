# Eric Zheng
# onyen: erzh
# PID: 730294463

from parse import CMDParser

class CLI_loop():
    def __init__(self, input_stream):
        self.parser = CMDParser()
        self.cmdinput = input_stream
        self.fpath = []
        self.buffer = []

    def run(self):
        # starts the state machine
        # entry state is reading for MAIL FROM cmds
        self.fpath = []
        self.buffer = []
        while(self._expect_mailf() == 0):
            pass
        
    def _expect_mailf(self):
        cmd = self.cmdinput.readline()

        # TODO when is the user allowed to exit with ctrl-D
        # only at mail-from or elsewhere as well?
        if cmd == '':
            return -2
        
        self._echo(cmd)
        self.parser.parse(cmd)

        if self.parser.status == 0:
            self.buffer.append(cmd)
            print('250 OK')
            self._expect_rcpt()
        else:
            if self.parser.status > 0:
                print("503 Bad sequence of commands")
            elif self.parser.bad_token[-3:] == 'cmd':
                print('500 Syntax error: command unrecognized')
            else:
                print('501 Syntax error in parameters or arguments')
            
            return -1
        return 0

    def _expect_rcpt(self):
        cmd = self.cmdinput.readline()

        self._echo(cmd)
        self.parser.parse(cmd)

        if self.parser.status == 1:
            self.buffer.append(cmd)
            self.fpath.append(self._get_path(cmd))
            print('250 OK')

            # check for more recipients following the first
            while(self.parser.status == 1):
                cmd = self.cmdinput.readline()

                self._echo(cmd)
                self.parser.parse(cmd)

                if self.parser.status == 1:
                    self.buffer.append(cmd)
                    self.fpath.append(self._get_path(cmd))
                    print('250 OK')
                # when the rcpt parse fails, check for data
                elif self.parser.status == 2:
                    # print intermediate response
                    print('354 Start mail input; end with <CRLF>.<CRLF>')
                    self._expect_data()
                    return

        if self.parser.status >= 0:
            print("503 Bad sequence of commands")
        elif self.parser.bad_token[-3:] == 'cmd':
            print('500 Syntax error: command unrecognized')
        else:
            print(self.parser.remainder)
            print('501 Syntax error in parameters or arguments')
    
    # used for parsing the data of the email itself and not the data cmd
    def _expect_data(self):
        for text in self.cmdinput:
            self._echo(text)
            if text == '.\n':
                break
            else:
                self.buffer.append(text)
        
        print('250 OK')

        for path in self.fpath:
            # open or create a file for each path specified in RCPT TO
            with open(f'forward/{path}', "a") as fout:
                fout.writelines(self.buffer)

    # takes a syntactically valid command and extracts the path
    def _get_path(self, cmd):
        return cmd[cmd.find('<')+1:cmd.find('>')]
    
    def _echo(self, line):
        if line != "":
            print(line[:-1] if line[-1] == '\n' else line)

if __name__ == "__main__":
    with open(0) as stdin:
        cli = CLI_loop(stdin)
        cli.run()