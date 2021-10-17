# Eric Zheng
# onyen: erzh
# PID: 730294463

from parse import CMDParser

class ServerLoop():
    def __init__(self, input_stream):
        self.parser = CMDParser()
        self.cmdinput = input_stream
        self.fpath = []
        self.buffer = []

    def run(self):
        # starts the state machine
        # entry state is reading for MAIL FROM cmd
        while(self._expect_mailf() == 0):
            pass
        
    def _expect_mailf(self):
        self.fpath = []
        self.buffer = []
        
        cmd = self.cmdinput.readline()
        
        self._echo(cmd)
        self.parser.parse(cmd)

        if self.parser.status == 0 and self.parser.cmd == 0:
            self.buffer.append(f'From: <{self._get_path(cmd)}>\n')
            print('250 OK')
            self._expect_rcpt()
        else:
            if self.parser.bad_token[-3:] == 'cmd':
                print('500 Syntax error: command unrecognized')
            elif self.parser.cmd != 0:
                print("503 Bad sequence of commands")
            else:
                print('501 Syntax error in parameters or arguments')
    
        return 0

    def _expect_rcpt(self):
        cmd = self.cmdinput.readline()

        self._echo(cmd)
        self.parser.parse(cmd)

        if self.parser.status == 0 and self.parser.cmd == 1:
            self.buffer.append(f'To: <{self._get_path(cmd)}>\n')
            self.fpath.append(self._get_path(cmd))
            print('250 OK')

            # check for more recipients following the first
            while(self.parser.status == 0):
                cmd = self.cmdinput.readline()

                self._echo(cmd)
                self.parser.parse(cmd)

                if self.parser.status == 0:
                    if self.parser.cmd == 1:
                        self.buffer.append(f'To: <{self._get_path(cmd)}>\n')
                        self.fpath.append(self._get_path(cmd))
                        print('250 OK')
                    # when the rcpt parse fails, check for data
                    elif self.parser.cmd == 2:
                        # print intermediate response
                        print('354 Start mail input; end with <CRLF>.<CRLF>')
                        self._expect_data()
                        return
                    # mail from command recieved
                    else:
                        print("503 Bad sequence of commands")
                        return

        if self.parser.bad_token[-3:] == 'cmd':
            print('500 Syntax error: command unrecognized')
        elif self.parser.cmd >= 0:
            print("503 Bad sequence of commands")
        else:
            print('501 Syntax error in parameters or arguments')
    
    # used for parsing the data of the email itself and not the data cmd
    def _expect_data(self):
        acc = False
        for text in self.cmdinput:
            self._echo(text)
            if text == '.\n':
                acc = True
                break
            else:
                self.buffer.append(text)
        
        if(acc is True):
            print('250 OK')

            for path in self.fpath:
                # open or create a file for each path specified in RCPT TO
                with open(f'forward/{path}', "a") as fout:
                    fout.writelines(self.buffer)
        else:
            exit(0)

    # takes a syntactically valid command and extracts the path
    def _get_path(self, cmd):
        return cmd[cmd.find('<')+1:cmd.find('>')]

    def _get_domain(self, cmd):
        return cmd[cmd.find('@')+1:]
    
    def _echo(self, line):
        if line != "":
            print(line[:-1] if line[-1] == '\n' else line)
        # eof inputted exit
        else:
            exit(0)

if __name__ == "__main__":
    with open(0) as stdin:
        cli = ServerLoop(stdin)
        cli.run()