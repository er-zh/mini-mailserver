# Eric Zheng
# onyen: erzh
# PID: 730294463

from parse import CMDParser

# constants labeling states
WAIT = "waiting" # for a connection
MF = "mail from"
RT = "rcpt to"
ERT = "extra rcpt to"
DATA = "data"
ERR = "error"
QUIT = "exit"

# constants for response codes
CONNECTEST = '220'
CMDOK = '250'
DATAPENDING = '354'
QUITREC = '221'
BADCMD = '500'
BADPARAM = '501'
BADORDER = '503'

class ServerLoop():
    def __init__(self, input_stream):
        self.parser = CMDParser()
        self.cmdinput = input_stream
        self.fpath = set()
        self.buffer = []
        self.rcode = ''

        self.transition = {
            (WAIT, CONNECTEST):MF,
            (MF, CMDOK):RT,
            (RT, CMDOK):ERT,
            (ERT, CMDOK):ERT,
            (ERT, DATAPENDING):DATA,
            (DATA, CMDOK):MF,
            # erroneous input recieved
            # ( / ), will be caught as exception
            # quit states
        }

        self.call = {
            MF:ServerLoop._expect_mailf,
            RT:ServerLoop._expect_rcpt,
            ERT:ServerLoop._expect_ercpt,
            DATA:ServerLoop._expect_data,
        }

    def run(self):
        # starts the state machine
        # entry state is reading for MAIL FROM cmd

        cstate = MF
        status = 0

        while status==0:
            status, rcode = self.call[cstate](self)

            try:
                cstate = self.transition[(cstate, rcode)]
            except KeyError:
                # if a error is recieved go back to the mail from state
                cstate = MF 
        
    def _expect_mailf(self):
        self.fpath = set()
        self.buffer = []
        
        cmd = self.cmdinput.readline()
        
        self._echo(cmd)
        self.parser.parse(cmd)

        if self.parser.status == 0 and self.parser.cmd == 0:
            self.buffer.append(f'From: <{self._get_path(cmd)}>\n')
            print('250 OK')
            # return transition to rcpt to state
            return (0, CMDOK)
        else:
            if self.parser.bad_token[-3:] == 'cmd':
                print('500 Syntax error: command unrecognized')
            elif self.parser.cmd != 0:
                print("503 Bad sequence of commands")
            else:
                print('501 Syntax error in parameters or arguments')
    
            return(0, ERR)

    def _expect_rcpt(self):
        cmd = self.cmdinput.readline()

        self._echo(cmd)
        self.parser.parse(cmd)

        if self.parser.status == 0 and self.parser.cmd == 1:
            self.buffer.append(f'To: <{self._get_path(cmd)}>\n')
            self.fpath.add(self._get_domain(self._get_path(cmd)))
            print('250 OK')
            
            return (0, CMDOK)
        else:
            if self.parser.bad_token[-3:] == 'cmd':
                print('500 Syntax error: command unrecognized')
            elif self.parser.cmd >= 0:
                print("503 Bad sequence of commands")
            else:
                print('501 Syntax error in parameters or arguments')

            return (0, ERR)

    def _expect_ercpt(self):
        cmd = self.cmdinput.readline()

        self._echo(cmd)
        self.parser.parse(cmd)

        if self.parser.status == 0:
            if self.parser.cmd == 1:
                self.buffer.append(f'To: <{self._get_path(cmd)}>\n')
                self.fpath.add(self._get_domain(self._get_path(cmd)))
                print('250 OK ')
                return (0, CMDOK)
            # when the rcpt parse fails, check for data
            elif self.parser.cmd == 2:
                # print intermediate response
                print('354 Start mail input; end with <CRLF>.<CRLF>')
                return (0, DATAPENDING)
            # mail from command recieved
            else:
                print("503 Bad sequence of commands")
                return (0, ERR)
        else:
            if self.parser.bad_token[-3:] == 'cmd':
                print('500 Syntax error: command unrecognized')
            elif self.parser.cmd >= 0:
                print("503 Bad sequence of commands")
            else:
                print('501 Syntax error in parameters or arguments')

            return (0, ERR)

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
            
            return (0, CMDOK)
        else:
            return (1, "whatever")

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