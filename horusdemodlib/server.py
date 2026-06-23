import _horus_api_cffi
import audioop
import logging
import sys
from enum import Enum
import os
import logging
from .decoder import decode_packet, hex_to_bytes
import horusdemodlib
import argparse
import sys
import json
from .demod import Mode, Frame, HorusLib
import socket 
import select

horus_api = _horus_api_cffi.lib

MAX_CLIENTS=1000


READ_ONLY = ( select.POLLIN |
              select.POLLPRI |
              select.POLLHUP |
              select.POLLERR )
READ_WRITE = READ_ONLY | select.POLLOUT

class HorusTCPInstance:
    def __init__(self,
             connection,
             mode,
             args,
             fout   
             ):
        self.h = HorusLib(mode=mode,tone_spacing=args.tonespacing, stereo_iq=args.q, verbose=int(args.v), callback=self.frame_callback, sample_rate=args.sample_rate, rate=int(args.rate))
        _decoder_info = f"Starting {args.mode} decoder, {args.rate} baud, {f'{args.tonespacing} Hz Tone Spacing, ' if args.tonespacing>0 else ''} {args.sample_rate} Hz sample rate {'IQ' if args.q else ''}"
        logging.info(_decoder_info)
        if args.fsk_lower > -99999 and args.fsk_upper > args.fsk_lower:
            self.h.set_estimator_limits(args.fsk_lower, args.fsk_upper)
            logging.info(f"Frequency Estimator Limits set to {args.fsk_lower}-{args.fsk_upper} Hz.")


        
        self.stats_counter = args.stats
        self.args = args
        self.buffer = b''
        self.fout = fout
        self.connection = connection

    def close(self):
        self.h.close()
        self.connection.close()

    def write(self,data):
        self.buffer += data



        output = self.h.add_samples(data)
        if self.args.v:
            if output:
                sys.stderr.write(f"Sync: {output.sync}  SNR: {output.snr}\n")
        if self.args.stats != None:
            stats_out = {
                "EbNodB": self.h.stats.snr_est,
                "ppm": self.h.stats.clock_offset,
                "f1_est": self.h.stats.f_est[0],
                "f2_est": self.h.stats.f_est[1]
            }
        
            if self.h.mfsk == 4:
                stats_out["f3_est"] = self.h.stats.f_est[2]
                stats_out["f4_est"] = self.h.stats.f_est[3]
            
            eye_diagram = []
            for i in range(self.h.stats.neyetr):
                eye_diagram.append([])
                for j in range(self.h.stats.neyesamp):
                    eye_diagram[i].append(self.h.stats.rx_eye[i][j])
            stats_out['eye_diagram'] = eye_diagram
            stats_out['samp_fft']=[0]*128 # broken in horus_demod.c - replicating the same output
            if self.args.g:
                print(json.dumps(stats_out))
            else:
                sys.stderr.write(json.dumps(stats_out)+"\n")

    def frame_callback(self, frame):
        # Print out only CRC-passing frames, unless we are in verbose mode
        if frame.crc_pass or self.args.v:

            if type(frame.data) == bytes:
                self.fout.write(frame.data.hex().upper())
            else:
                self.fout.write(frame.data)
        
            if self.args.c:
                if frame.crc_pass:
                    self.fout.write(f"  CRC OK")
                else:
                    self.fout.write(f"  CRC BAD")
            self.fout.write("\n")
            self.fout.flush()


def main():
    parser = argparse.ArgumentParser(
                    prog='horus_server',
                    description='Receives audio stream via TCP and demodulates the frames')    

    modes = ["RTTY","RTTY7N1","RTTY8N2","RTTY7N2","BINARY"]
    parser.add_argument('-m','--mode',choices=modes+[x.lower() for x in modes], default="binary", help="RTTY or binary Horus protocol")
    parser.add_argument('--sample-rate',default=48000, type=int,help="Audio sample rate")
    parser.add_argument('--rate',default=100, type=int,help="Customise modem baud rate. Default: (depends on mode)")
    parser.add_argument('--tcp-port',default=4921, type=int,help="TCP port to listen for samples")
    parser.add_argument('--tonespacing',default=-1, type=int,help="Transmitter Tone Spacing (Hz) Default: Not used.")
    parser.add_argument('-t','--stats', default=None,  nargs='?', const=8, type=int, help="Print out modem statistics to stderr in JSON") # TODO 
    parser.add_argument('-g', action="store_true", default=False,help="Emit Stats on stdout instead of stderr")
    parser.add_argument('-q', action="store_true",default=False,help="use stereo (IQ) input")
    parser.add_argument('-v', action="store_true",default=False,help="verbose debug info")
    parser.add_argument('-c', action="store_true",default=False,help="display CRC results for each packet")
    parser.add_argument('-u',"--fsk_upper", type=int, action="store",default=False,help="Estimator FSK upper limit")
    parser.add_argument('-b',"--fsk_lower", type=int, action="store",default=False,help="Estimator FSK lower limit")
    parser.add_argument('output',nargs='?',action='store', default=sys.stdout, help="Output filename")

    args = parser.parse_args()

    if args.mode.lower() == 'rtty7n2' or args.mode.lower() == 'rtty':
        mode = Mode.RTTY_7N2
    elif args.mode.lower() == 'rtty7n1':
        mode = Mode.RTTY_7N1
    elif args.mode.lower() == 'rtty8n2':
        mode = Mode.RTTY_8N2
    else:
        mode = Mode.BINARY


    if type(args.output) == type(sys.stdout) or args.output == "-":
        fout = sys.stdout
    else:
        fout = open(args.output, "w")



    # Setup Logging
    log_level = logging.INFO
    if args.v:
        log_level = logging.DEBUG
    
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=log_level
    )

    logging.info(f"horusdemodlib v{horusdemodlib.__version__} - horus_demod")


    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", args.tcp_port))
    s.listen(MAX_CLIENTS)
    


    poller = select.poll()
    poller.register(s, READ_ONLY)
    fd_to_socket = { s.fileno(): s}

    while 1:
        events = poller.poll(1000) # don't block forever
        for fd, flag in events: 
            p = fd_to_socket[fd]
            if flag & (select.POLLIN | select.POLLPRI):

                if p is s: # server
                    connection, client_address = p.accept()
                    logging.info(f"New client connected: {client_address}")
                    connection.setblocking(0)
                    fd_to_socket[ connection.fileno() ] = HorusTCPInstance(connection=connection, mode=mode,args=args, fout=fout)
                    poller.register(connection, READ_ONLY)
                    
                else:
                    data = p.connection.recv(1024)
                    if data:
                        p.write(data)
                        # Add output channel for response
                        poller.modify(p.connection, READ_WRITE)

                    else:
                        logging.info(f"Connection with {client_address} lost")
                        # Stop listening for input on the connection
                        poller.unregister(p.connection)
                        p.close()
                        
                        del fd_to_socket[fd]

    

# workaround for poetry install script
if __name__ == "__main__":
    main()