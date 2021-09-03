# Eric Zheng
# onyen: erzh
# PID: 730294463

from parse import CMDParser

class CLI_loop():
    def __init__(self, input_stream):
        self.parser = CMDParser()
        self.cmdinput = input_stream

    def run(self):
        # starts the state machine
        # entry state is reading for MAIL FROM cmds

        self._expect_mailf()
        

    def _expect_mailf(self):
        cmd = self.cmdinput.readline()

        # TODO when is the user allowed to exit with ctrl-D
        # only at mail-from or elsewhere as well?
        if cmd == '':
            return
        
        self._echo(cmd)
        self.parser.parse_mail_from_cmd(cmd)

        if self.parser.status == 0:
            print('250 OK')
            self._expect_rcpt()
        else:
            if self.parser.bad_token[-3:] == 'cmd':
                print('500 Syntax error: command unrecognized')
            else:
                print('501 Syntax error in parameters or arguments')

    def _expect_rcpt(self):
        cmd = self.cmdinput.readline()

        self._echo(cmd)
        self.parser.parse_rcpt_to_cmd(cmd)

        if self.parser.status == 0:
            print('250 OK')

            # check for more recipients following the first
            while(self.parser.status == 0):
                cmd = self.cmdinput.readline()

                self._echo(cmd)
                self.parser.parse_rcpt_to_cmd(cmd)

                if self.parser.status == 0:
                    print('250 OK')
                else:
                    # when the rcpt parse fails, check for data
                    self.parser.parse_data_cmd(cmd)

                    if self.parser.status == 0:
                        print('354 Start mail input; end with <CRLF>.<CRLF>')
                        self._expect_data()
                        return

        if self.parser.bad_token[-3:] == 'cmd':
            print('500 Syntax error: command unrecognized')
        else:
            print('501 Syntax error in parameters or arguments')
    
    # used for parsing the data of the email itself and not the data cmd
    def _expect_data(self):
        print('arrived')
    
    def _echo(self, line):
        print(line[:-1] if line[-1] == '\n' else line)


if __name__ == "__main__":
    with open(0) as stdin:
        cli = CLI_loop(stdin)
        cli.run()