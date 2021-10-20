import socket
import re
from sys import argv, stderr

# PORTNUM = 8000 + 4463
BUFSIZE = 1024

# regex for checking correct mailbox format
mb_regex = r"^[0-9a-zA-z!#$%^&*`~_|?=+/-]+@[a-zA-Z][0-9a-zA-Z]*(?:.[a-zA-Z][0-9a-zA-Z]*)*$"
mb_check = re.compile(mb_regex)

# constants that label the states of the client program
USRIPT = "user input"
HELO = "greet hello"
MF = "mail from"
RT = "rcpt to"
ERT = "extra rcpt to"
DATA = "data"
ERR = "error"
END = "done"

# constants labeling the return codes
CONNECTEST = '220'
CONNECTTMN = '221'
CMDOK = '250'
DATAPENDING = '354'
QUITREC = '221'
BADCMD = '500'
BADPARAM = '501'
BADORDER = '503'

class ClientLoop():
    def __init__(self, hostname, portnum):
        self.msg_contents = None
        # TODO replace this with server socket connection
        self.hname = hostname
        self.pnum = portnum
        self.servsock = None

        self.transition = {
            (USRIPT, HELO):HELO,
            (HELO, CMDOK):MF,
            (MF, CMDOK):RT,
            (RT, CMDOK):ERT,
            (ERT, DATAPENDING):END,
            # does this directly transition into a quit state?
            (DATA, CMDOK):USRIPT,
            # TODO this transition may not longer be correct
            # or necessary
            (DATA, END):END,
            # erroneous ack codes recieved
            (MF, BADCMD):ERR,
            (RT, BADCMD):ERR,
            (ERT, BADCMD):ERR,
            (DATA, BADCMD):ERR,
            (MF, BADPARAM):ERR,
            (RT, BADPARAM):ERR,
            (ERT, BADPARAM):ERR,
            (DATA, BADPARAM):ERR,
            (MF, BADORDER):ERR,
            (RT, BADORDER):ERR,
            (ERT, BADORDER):ERR,
            (DATA, BADORDER):ERR,
            # once the end is reached there are
            # no more states to transition into
            (END, END):'',
            (ERR, END):''
        }

        self.call = {
            USRIPT:ClientLoop._get_user_input,
            HELO:ClientLoop._send_hello,
            MF:ClientLoop._send_mailto,
            RT:ClientLoop._send_rcptto,
            ERT:ClientLoop._send_ercptto,
            DATA:ClientLoop._send_data,
            END:ClientLoop._send_quit,
            ERR:ClientLoop._send_quit
        }
        # all states will perform some action corresponding to
        # data read from the forwards file, then wait for an
        # ack code

    def run(self):
        # start the state machine
        # initial state is expecting user input
        cstate = USRIPT
        status = 0
        while status == 0:
            status, rcode = self.call[cstate](self)

            try:
                cstate = self.transition[(cstate, rcode)]
            except KeyError:
                cstate = ERR
        
        # TODO ConnectionRefusedErrors need to be accounted for
    
    # TODO quit on eof
    # TODO make this code neater
    def _get_user_input(self):
        with open(0) as stdin:
            # expects a single mailbox
            print('From:')
            sender = stdin.readline().rstrip()

            while mb_check.match(sender) is None:
                print(f'Sender mailbox has syntax error')

                print('From:')
                sender = stdin.readline().rstrip()

            # expects one or more mailboxes, separated by a ","
            # with an optional trailing space
            stxerr = False
            print('To:')
            recipients = stdin.readline().split(',')
            recipients = list(map(lambda a: a.rstrip().lstrip(), recipients))
            for i, rcpt in enumerate(recipients, 1):
                stxerr = mb_check.match(rcpt) is None
                if stxerr:
                    print(f'Recipient mailbox at position {i} has syntax error')
                    break
            
            while stxerr:
                print('To:')
                recipients = stdin.readline().split(',')
                recipients = list(map(lambda a: a.rstrip().lstrip(), recipients))
                for i, rcpt in enumerate(recipients, 1):
                    stxerr = mb_check.match(rcpt) is None
                    if stxerr:
                        print(f'Recipient mailbox at position {i} has syntax error')
                        break

            # get the message subject
            print('Subject:')
            subject = stdin.readline()

            # get the message
            print('Message:')
            msg = []
            line = stdin.readline()
            while line != '.\n':
                msg.append(line)
                line = stdin.readline()

        self.msg_contents = [
            sender,
            recipients,
            subject,
            msg
        ]

        return (0, HELO)

    def _send_hello(self):
        self.servsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.servsock.connect((self.hname, self.pnum))

        rc = self._get_ack()

        cmd = f'HELO {socket.gethostname()}\n'
        self.servsock.send(cmd.encode())

        return (0, self._get_ack())

    def _send_mailto(self):
        cmd = f'MAIL FROM: <{self.msg_contents[0]}>\n'
        self.servsock.send(cmd.encode())

        return (0, self._get_ack())

    def _send_rcptto(self):
        ack = ''
        for rcpt in self.msg_contents[1]:
            cmd = f'RCPT TO: <{rcpt}>\n'
            self.servsock.send(cmd.encode())

            ack = self._get_ack()
            if ack != CMDOK:
                break

        return (0, ack)

    # no longer needs to handle extra rcpt tos
    # just needs to send DATA cmd
    def _send_ercptto(self):
        self.servsock.send('DATA\n'.encode())
        
        return (0, self._get_ack())

    def _send_data(self):
        # send the header of the email
        msg = f'From: <{self.msg_contents[0]}>\nTo: '
        self.servsock.send(msg.encode())

        msg = ''
        for rcpt in self.msg_contents[1]:
            msg += f'<{rcpt}>'

            self.servsock.send(msg.encode())
            msg = ', '
        
        # subject input is not stripped, so msg_contents[2] should already have one
        # newline at the end, thus only needs one more for the empty line delineating
        # the header from the body of the email
        msg = f'\nSubject: {self.msg_contents[2]}\n'
        self.servsock.send(msg.encode())

        # send the body of the email
        for msg in self.msg_contents[3]:
            self.servsock.send(msg.encode())

        # end the data transmission
        self.servsock.send('.\n'.encode())
        
        return (0, self._get_ack())
    
    def _send_quit(self):
        self.servsock.send('QUIT\n'.encode())

        rc = self._get_ack()

        return (1, END)
    
    # read in the next input line
    def _advance_read(self):
        self.cline = self.ff.readline()

    def _get_ack(self):
        ack = self.servsock.recv(BUFSIZE).decode()
        # TODO delete vestigial printouts
        errprint(ack)

        # recieved ack code must have the correct number
        # in addition to being a well-formed message
        # ie must follow <code><whitespace><*+><CRLF>
        try:
            if (ack[3] == ' ' or ack[3] == '\t') and ack[4:-1] != '':
                # only the error code itself is returned
                return ack[:3]
        except IndexError:
            pass
        return ''

def errprint(line):
    # get rid of the '\n' at the end of a line of user input
    print(line[:-1], file=stderr)

if __name__ == "__main__":
    if len(argv) < 3:
        # insufficient args recieved
        exit(1)
    else:
        serv_hostname = argv[1]
        serv_portnum = int(argv[2])

        cli = ClientLoop(serv_hostname, serv_portnum)

        cli.run()