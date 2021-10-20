# Eric Zheng
# onyen: erzh
# PID: 730294463

import socket
from parse import CMDParser


# constant port number
# TODO reimplement as an argument
PORTNUM = 8000 + 4463
MAX_CONNECTION_REQS = 1
BUFSIZE = 1024

# constants labeling states
WAIT = "waiting" # for a connection
MF = "mail from"
RT = "rcpt to"
ERT = "extra rcpt to"
DATA = "data"
QUIT = "disconnect"
ERR = "error"

# constants for response codes
CONNECTEST = '220'
CONNECTTMN = '221'
CMDOK = '250'
DATAPENDING = '354'
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

        self.sock = None
        self.csock = None
        self.addr = None

        self.transition = {
            (WAIT, CMDOK):MF,
            (MF, CMDOK):RT,
            (RT, CMDOK):ERT,
            (ERT, CMDOK):ERT,
            (ERT, DATAPENDING):DATA,
            (DATA, CMDOK):QUIT,
            # erroneous input recieved
            # ( / ), will be caught as exception
            # quit states
            (QUIT, CONNECTTMN):WAIT
        }

        self.call = {
            WAIT:ServerLoop._waitfor_connection,
            MF:ServerLoop._expect_mailf,
            RT:ServerLoop._expect_rcpt,
            ERT:ServerLoop._expect_ercpt,
            DATA:ServerLoop._expect_data,
            QUIT:ServerLoop._expect_quit
        }

    def run(self):
        # creates a socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', PORTNUM))
        self.sock.listen(MAX_CONNECTION_REQS)

        # starts the state machine
        # entry state is reading for MAIL FROM cmd
        cstate = WAIT

        while True:
            rcode = self.call[cstate](self)

            try:
                cstate = self.transition[(cstate, rcode)]
            except KeyError:
                # if a error is recieved go back to the mail from state
                cstate = QUIT

        # need a try except for socket OSErrors
        
    def _waitfor_connection(self):
        self.csock, self.addr = self.sock.accept()

        self._so_sock('220 ' + socket.gethostname())

        # HELO cmd response from client
        cmd = self._rf_sock()

        self.parser.parse(cmd)

        if self.parser.status == 0 and self.parser.cmd == 3:
            self._so_sock('250 Hello ' + cmd[4:].rstrip().lstrip() + ', pleased to meet you')
        else:
            if self.parser.bad_token[-3:] == 'cmd':
                self._so_sock('500 Syntax error: command unrecognized')
            elif self.parser.cmd != 3:
                self._so_sock("503 Bad sequence of commands")
            else:
                self._so_sock('501 Syntax error in parameters or arguments')

            return ERR

        return CMDOK

    def _expect_mailf(self):
        self.fpath = set()
        self.buffer = []
        
        cmd = self._rf_sock()

        self.parser.parse(cmd)

        if self.parser.status == 0 and self.parser.cmd == 0:
            self.buffer.append(f'From: <{self._get_path(cmd)}>\n')
            
            self._so_sock('250 OK')
            # return transition to rcpt to state
            return CMDOK
        else:
            if self.parser.bad_token[-3:] == 'cmd':
                self._so_sock('500 Syntax error: command unrecognized')
            elif self.parser.cmd != 0:
                self._so_sock("503 Bad sequence of commands")
            else:
                self._so_sock('501 Syntax error in parameters or arguments')
    
            return ERR

    def _expect_rcpt(self):
        cmd = self._rf_sock()
        
        self.parser.parse(cmd)

        if self.parser.status == 0 and self.parser.cmd == 1:
            # TODO is the server writing the recipients and senders extraneous now that
            # the client sends that information in the header of the email?
            self.buffer.append(f'To: <{self._get_path(cmd)}>\n')
            self.fpath.add(self._get_domain(self._get_path(cmd)))
            
            self._so_sock('250 OK')
            
            return CMDOK
        else:
            if self.parser.bad_token[-3:] == 'cmd':
                self._so_sock('500 Syntax error: command unrecognized')
            elif self.parser.cmd >= 0:
                self._so_sock("503 Bad sequence of commands")
            else:
                self._so_sock('501 Syntax error in parameters or arguments')

            return ERR

    def _expect_ercpt(self):
        cmd = self._rf_sock()
        
        self.parser.parse(cmd)

        if self.parser.status == 0:
            if self.parser.cmd == 1:
                self.buffer.append(f'To: <{self._get_path(cmd)}>\n')
                self.fpath.add(self._get_domain(self._get_path(cmd)))
                
                self._so_sock('250 OK')
                return CMDOK
            # when the rcpt parse fails, check for data
            elif self.parser.cmd == 2:
                # print intermediate response
                self._so_sock('354 Start mail input; end with <CRLF>.<CRLF>')
                return DATAPENDING
            # mail from command recieved
            else:
                self._so_sock("503 Bad sequence of commands")
                return ERR
        else:
            if self.parser.bad_token[-3:] == 'cmd':
                self._so_sock('500 Syntax error: command unrecognized')
            elif self.parser.cmd >= 0:
                self._so_sock("503 Bad sequence of commands")
            else:
                self._so_sock('501 Syntax error in parameters or arguments')

            return ERR

    # used for parsing the data of the email itself and not the data cmd
    def _expect_data(self):
        acc = False
        text = self._rf_sock()
        while text != '':
            if text[-3:] == '\n.\n':
                self.buffer.append(text[:-2])
                acc = True
                break
            
            self.buffer.append(text)
            
            text = self._rf_sock()
        
        if acc is True:
            self._so_sock('250 OK')

            for path in self.fpath:
                # open or create a file for each path specified in RCPT TO
                with open(f'forward/{path}', "a") as fout:
                    fout.writelines(self.buffer)
            
            return CMDOK
        
        return "i think this should be ERR?"
    
    def _expect_quit(self):
        cmd = self._rf_sock()
        
        self.parser.parse(cmd)

        if self.parser.status == 0 and self.parser.cmd == 4:
            self._so_sock('221 ' + socket.gethostname() + ' closing connection')

            self.csock.close()

            self.csock = None
            self.addr = None

            return CONNECTTMN
        else:
            if self.parser.bad_token[-3:] == 'cmd':
                self._so_sock('500 Syntax error: command unrecognized')
            elif self.parser.cmd != 4:
                self._so_sock("503 Bad sequence of commands")
            else:
                self._so_sock('501 Syntax error in parameters or arguments')

            return ERR

    # takes a syntactically valid command and extracts the path
    def _get_path(self, cmd):
        return cmd[cmd.find('<')+1:cmd.find('>')]

    # takes a path and extracts the domain name
    def _get_domain(self, cmd):
        return cmd[cmd.find('@')+1:]

    def _echo(self, line):
        if line != "":
            print(line[:-1] if line[-1] == '\n' else line)
        # eof inputted exit
        # TODO change behavior to run indefinitely
        else:
            exit(0)
    
    # read data from the connection socket
    def _rf_sock(self):
        data = self.csock.recv(BUFSIZE)

        # TODO actually handle case where nothing is recv'd
        if data == b'':
            print("nothing recv'd")
        
        data = data.decode()

        # TODO delete unecessary printouts
        self._echo(data)

        return data
    
    # send response code back over connection socket
    def _so_sock(self, msg):
        msg = msg + '\n'
        self.csock.send(msg.encode())

if __name__ == "__main__":
    with open(0) as stdin:
        cli = ServerLoop(stdin)
        cli.run()