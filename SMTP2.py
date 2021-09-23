from sys import argv, stderr

MF = "mail from"
RT = "rcpt to"
ART = "extra rcpt to"
DATA = "data"
ERR = "error"

class ClientLoop():
    def __init__(self, forwardfile, inputstream):
        self.ff = forwardfile
        self.input = inputstream
        self.buffer = ''

        self.transition = {
            (MF, '250'):RT,
            (RT, '250'):ART,
            (ART, '250'):ART,
            (ART, '354'):DATA,
            (DATA, '250'):MF
        }
        self.call = {
            MF:ClientLoop._send_mailto,
            RT:ClientLoop._send_rcptto,
            ART:ClientLoop._send_additionalto,
            DATA:ClientLoop._send_data
        }

    def run(self):
        cstate = MF
        status = 0
        while status == 0:
            status, rcode = self.call[cstate]()

            cstate = self.transition[(cstate, rcode)]
    
    # expects a well formed From: line in an email
    def _send_mailto(self):
        line = self.ff.readline()

        if line[:5] == 'From:':
            print('MAIL FROM:' + line[5:], end='')

            ack = self.input.readline()
            rcode = ack[:3] 

            return (0, rcode)
        return (1, '')

    # expects a well formed To: line in an email
    # or can accept a data command
    def _send_rcptto(self, line):
        line = self.ff.readline()

        if line[:3] == 'To:':
            print('RCPT TO:'+ line[3:], end='')

            ack = self.input.readline()
            rcode = ack[:3]

            return (0, rcode)
        return (1, '')

    def _send_additionalto(self, line):
        if line[:3] == 'To:':
            print('RCPT TO:'+ line[3:], end='')

            ack = self.input.readline()
            rcode = ack[:3]

            return (0, rcode)
        else:
            print('DATA')
            self.buffer = line

            ack = self.input.readline()
            rcode = ack[:3]

            return (0, rcode)

    def _send_data(self, line):
        if self.buffer != '':
            print(line, end='')
            self.buffer = ''
        print(line, end='')

def errprint(line):
    print(line, file=stderr)

if __name__ == "__main__":
    # TODO do improper inputs need accounting
    if len(argv) < 2:
        # insufficient args recieved
        exit(1)
    else:
        forward_file = argv[1]

    try:
        with open(forward_file, 'r') as ff, open(0) as stdin:
            cli = ClientLoop(ff, stdin)
    except FileNotFoundError:
        print('forward file not able to be located')