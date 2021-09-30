from sys import argv, stderr

MF = "mail from"
RT = "rcpt to"
ERT = "extra rcpt to"
DATA = "data"
ERR = "error"
END = "done"

class ClientLoop():
    def __init__(self, forwardfile, inputstream):
        self.ff = forwardfile
        self.input = inputstream
        self.cline = ''
        self.eof_reached = False

        self.transition = {
            (MF, '250'):RT,
            (RT, '250'):ERT,
            (ERT, '250'):ERT,
            (ERT, '354'):DATA,
            (DATA, '250'):MF,
            (DATA, END):END,
            # erroneous ack codes recieved
            (MF, '500'):ERR,
            (RT, '500'):ERR,
            (ERT, '500'):ERR,
            (DATA, '500'):ERR,
            (MF, '501'):ERR,
            (RT, '501'):ERR,
            (ERT, '501'):ERR,
            (DATA, '501'):ERR,
            # once the end is reached there are
            # no more states to transition into
            (END, END):'',
            (ERR, END):''
        }

        self.call = {
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
        cstate = MF
        status = 0
        while status == 0:
            status, rcode = self.call[cstate](self)

            try:
                cstate = self.transition[(cstate, rcode)]
            except KeyError:
                cstate = ERR
    
    # expects a well formed From: line in an email
    def _send_mailto(self):
        # only need to get the next line if nothing
        # has been read yet
        if self.cline == '':
            self._advance_read()

        if self.cline[:5] == 'From:':
            print('MAIL FROM:' + self.cline[5:], end='')

            return (0, self._get_ack())
        return (1, '')

    # expects a well formed To: line in an email
    # or can accept a data command
    def _send_rcptto(self):
        self._advance_read()

        if self.cline[:3] == 'To:':
            print('RCPT TO:'+ self.cline[3:], end='')

            return (0, self._get_ack())
        return (1, '')

    def _send_ercptto(self):
        self._advance_read()
        got_rcpt = True
        if self.cline[:3] == 'To:':
            print('RCPT TO:'+ self.cline[3:], end='')
        else:
            print('DATA')
            got_rcpt = False
        
        ack = self._get_ack()
        # need to manually identify that the correct ack has been recieved
        # since the current state can't distinguish between whether it has successfully
        # processed a data command or another rcpt to command
        if (got_rcpt and ack == '250') or (not got_rcpt and ack == '354'):
            return (0, ack)
        else:
            return (0, END)

    def _send_data(self):
        # does not need to advance read here
        # bc email data was detected already but
        # only a DATA command was issued
        finished = True
        while self.cline != '':
            if self.cline[:5] == "From:":
                finished = False
                break
            print(self.cline, end='')
            
            self._advance_read()

        print('.')
        # if the while loop is exitted with ''
        # then EOF has been encountered
        if finished:
            self._get_ack()
            return(0, END)
        return (0, self._get_ack())
    
    def _send_quit(self):
        print('QUIT')

        return (1, END)
    
    # read in the next input line
    def _advance_read(self):
        self.cline = self.ff.readline()

    def _get_ack(self):
        ack = self.input.readline()
        errprint(ack)

        # recieved ack code must have the correct number
        # in addition to being a well-formed message
        # ie must follow <code><whitespace><*+><CRLF>
        try:
            if (ack[3] == ' ' or ack[3] == '\t') and ack[4:-1] != '':
                return ack[:3]
        except IndexError:
            pass
        return ''

def errprint(line):
    # get rid of the '\n' at the end of a line of user input
    print(line[:-1], file=stderr)

if __name__ == "__main__":
    if len(argv) < 2:
        # insufficient args recieved
        exit(1)
    else:
        forward_file = argv[1]

    try:
        with open(forward_file, 'r') as ff, open(0) as stdin:
            cli = ClientLoop(ff, stdin)

            cli.run()
    except FileNotFoundError:
        # file name arg does not refer to a findable file
        exit(2)