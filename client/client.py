import http.client
import json
import threading
import socket
import random
from PIL import Image
import numpy
from colorama import Fore, Back


server_ip = '127.0.0.1'
server_port = 8000
client_name = None


class ServerConnection:

    def __init__(self):
        self.conn = None

    def connect(self):
        try:
            print(Fore.RED+"Connecting to server...")
            conn = http.client.HTTPConnection(server_ip, server_port, timeout=5)
            print(Fore.RED+"Connection succeed")
            self.conn = conn
            return True
        except:
            print(Fore.RED+"Can not connect to server")
            return False

    def post_user_data(self, name, ip, port):
        user_dict = {'name': name, 'ip': ip, 'port': port}
        user_dict = json.dumps(user_dict)
        data = user_dict.encode('utf-8')
        headers = {'Content-Length': str(len(data))}
        try:
            self.conn.request("POST", "name", data, headers)
            response = self.conn.getresponse()
            if response.status == 200:
                print(Fore.RED+"Name accepted")
                return True
            else:
                print(Fore.RED+"cannot use this name")
                return "retry_name"

        except:
            print(Fore.RED+"Connection failed")
            return False

    def get_list(self):
        try:
            print(Fore.RED+"Getting list of users...")
            self.conn.request("GET", "list")
            response = self.conn.getresponse()
            if response.status == 200:
                rj = response.read()
                r = json.loads(rj.decode("utf-8"))
                return r
            else:
                print(Fore.RED+"No user yet")
                return "no_user_yet"

        except:
            print(Fore.RED+"Connection failed")
            return False

    def get_user_data(self, name):
        try:
            print(Fore.RED+"Getting user data")
            self.conn.request("GET", "user/" + name)
            response = self.conn.getresponse()
            if response.status == 200:
                rj = response.read()
                r = json.loads(rj.decode("utf-8"))
                return r
            else:
                print(Fore.RED+"User is not valid")
                return None

        except :
            print(Fore.RED+"Connection failed")
            return False
        

class DecEnc :

    def encode_wh_im_to_bytes(w,h):
        b = w.to_bytes(4,'big')
        b += h.to_bytes(4,'big')
        c = DecEnc.checksum(b)
        return b + c


    def decode_wh_im_to_int(b:bytes):
        if DecEnc.checksum(b[0:8]) != b[8:]:
            return False
        w = int.from_bytes(b[:4], "big")
        h = int.from_bytes(b[4:8], "big")
        return w, h

    def encode_im_chunk_to_bytes(pix,hi,width):
        by = hi.to_bytes(4,'big')
        for wi in range(width):
            r,g,b = pix[wi,hi]
            by += r.to_bytes(1,'big')
            by += g.to_bytes(1,'big')
            by += b.to_bytes(1,'big')
        c = DecEnc.checksum(by)
        return by + c

    def decode_im_chunk_to_int(by:bytes,pix,width):
        sc = width*3+4
        if DecEnc.checksum(by[0:sc]) != by[sc:]:
            return False
        hi = int.from_bytes(by[:4], "big")
        for wi in range(width):
            index  = 3 * wi
            r = int.from_bytes(by[index+4:index+4+1], "big")
            g = int.from_bytes(by[index+4+1:index+4+1+1], "big")
            b = int.from_bytes(by[index+4+2:index+4+2+1], "big")
            pix[wi,hi] = (r,g,b)
        return hi

    def encode_im_hi(hi):
        by = hi.to_bytes(4,'big')
        c = DecEnc.checksum(by)
        return by + c

    def decode_im_hi(by:bytes):
        if DecEnc.checksum(by[0:4]) != by[4:]:
            return False
        hi = int.from_bytes(by[:4], "big")
        return hi

        
    def checksum(data):
        """
        Calculate the 1-Byte checksum for an array of bytes.
        """
        return bytes([sum(data) & 0xFF])



class ClientSession:
    def __init__(self):
        self.name = None
        self.ip = socket.gethostbyname(socket.gethostname())
        self.welcome_port = random.randint(49152,65535)
        self.welcome_sock = None

    def initialize(self):
        self.welcome_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.welcome_sock.bind((self.ip, self.welcome_port))
        t = threading.Thread(target=self.wait_for_peers)
        t.start()

    def wait_for_peers(self):
        while True:
            msg, adr = self.welcome_sock.recvfrom(1024)
            if msg is not None and msg.decode("utf-8") == 'IMG':
                self.welcome_sock.sendto('ACK'.encode("utf-8"),adr)
                t = threading.Thread(target=self.send_img, args=(adr,))
                t.start()
            elif msg is not None and msg.decode("utf-8") == 'TXT':
                self.welcome_sock.sendto('ACK'.encode("utf-8"),adr)
                t = threading.Thread(target=self.send_txt, args=(adr,))
                t.start()


    def send_img(self, adr):
        try:
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            data_sock.settimeout(10.0)
            im = Image.open('my_file.jpg')
        except Exception as e:
            print(Fore.YELLOW+"Unable to send data to peer")
            data_sock.close()
            return False
        
        pix = im.load()  # getting pixel values
        width, height = im.size  # Get the width and height of the image for iterating over
        B = DecEnc.encode_wh_im_to_bytes(width,height)
        try:
            data_sock.sendto(B,adr)
            msg , a = data_sock.recvfrom(1024)
            if msg.decode("utf-8") != "ACK_SIZE":
                return False
        except:
            data_sock.close()
            return False
        

        for hi in range(height):
            B = DecEnc.encode_im_chunk_to_bytes(pix,hi,width)
            data_sock.sendto(B,adr)


        data_sock.sendto("FIN".encode("utf-8"),adr)

        while True:
            try:
                msg , a = data_sock.recvfrom(1024)
            except:
                data_sock.close()
                return False
            
            try: 
                text = msg.decode("utf-8")
            except:
                text = None
            
            if text is not None and text == "COMPLETE":
                data_sock.close()
                return True
            elif text is not None and text == "FIN":
                pass
            else:
                result = DecEnc.decode_im_hi(msg)
                if result is not False:
                    hi = result
                    B = DecEnc.encode_im_chunk_to_bytes(pix,hi,width)
                    data_sock.sendto(B,adr)




        
            
         
        
        
        

    def send_txt(self, adr):
        try:
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.settimeout(1.0)
            data_sock.connect(adr)
            file = open('my_file.txt', 'rb')
            data = file.read()
            data_sock.send(data)
            file.close()
            data_sock.close()

        except :
            print(Fore.YELLOW+"Unable to send data to peer")
            return

    

    def req_img(self, target_ip, target_port,retry_attemps = 0):
        num = 0
        if retry_attemps == 3:
            print(Fore.YELLOW+"Image file transfer was unsuccessful.")
            return False
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        req_port = random.randint(49152,65535)
        sock.bind((self.ip, req_port))  #just a random port
        sock.sendto('IMG'.encode("utf8"), (target_ip, target_port))
        sock.settimeout(1.0)
        # waiting for ack
        try:
            ack , adr = sock.recvfrom(1024)
            if ack.decode("utf-8") == "ACK":
                pass
            else:
                return self.req_img(target_ip,target_port,retry_attemps= retry_attemps+1)
        except:
            return self.req_img(target_ip,target_port,retry_attemps= retry_attemps+1)
        
        # recieving image
        sock.settimeout(10.0)
        # getting image size
        try:
            msg , adr = sock.recvfrom(1024)
        except:
            return self.req_img(target_ip, target_port,retry_attemps = retry_attemps+1)
        
        result = DecEnc.decode_wh_im_to_int(msg)
        if result is False:
            return self.req_img(target_ip, target_port,retry_attemps = retry_attemps+1)
        else:
            sock.sendto("ACK_SIZE".encode("utf-8"), adr)
            width , height = result
            im = Image.new(mode="RGB" , size=(width,height))
            pix = im.load()

        # getting image pixels:
        pix_status = numpy.full((height), False, dtype=bool)
        print(Fore.YELLOW+"Getting image from peer...")
        while True:
            try:
                msg , a = sock.recvfrom(4096)
            except:
                return self.req_img(target_ip, target_port,retry_attemps = retry_attemps+1)
            
            try: 
                text = msg.decode("utf-8")
            except:
                text = None

            if text is not None and text == "FIN":
                all_true = True
                for hi in range(height):
                    if pix_status[hi] == False:
                        all_true = False
                        B = DecEnc.encode_im_hi(hi)
                        sock.sendto(B,adr)

                if all_true is False :           
                    sock.sendto("FIN".encode("utf-8"),adr)
                else:
                    sock.sendto("COMPLETE".encode("utf-8"),adr)
                    break


            else:
                result = DecEnc.decode_im_chunk_to_int(msg,pix,width)
                if result is not False:
                    pix_status[result] = True
                num+=1


        im.save(target_ip+'.jpg')
        print(Fore.YELLOW+"Image file transfer was done successfully.")
        sock.close()
        return True

        


            






    def req_txt(self, target_ip, target_port, retry_attemps = 0):
        if retry_attemps == 3:
            print(Fore.YELLOW+"Text file transfer was unsuccessful.")
            return False
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        req_port = random.randint(49152,65535)
        sock.bind((self.ip, req_port))  #just a random port
        sock.sendto('TXT'.encode("utf-8"), (target_ip, target_port))
        sock.settimeout(1.0)
        # waiting for ack
        try:
            ack , adr = sock.recvfrom(1024)
            if ack.decode("utf-8") == "ACK":
                pass
            else:
                return self.req_txt(target_ip,target_port,retry_attemps= retry_attemps+1)
        except:
            return self.req_txt(target_ip,target_port,retry_attemps= retry_attemps+1)
                
        # waiting for other peer to connect
        serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serv.bind((self.ip, req_port))
        serv.listen(1)
        serv.settimeout(1.0)
        try:
            data_sock, addr = serv.accept()
            serv.close()
            try:
                print(Fore.YELLOW+"Recieving text from peer...")
                data_sock.settimeout(1.0)
                data = data_sock.recv(1048576)
            except:
                data_sock.close()
                return self.req_txt(target_ip, target_port,retry_attemps=retry_attemps+1)
            
            try:
                file = open(target_ip + '.txt', 'wb')
                file.write(data)
                file.close()
                print(Fore.YELLOW+"Text file transfer was done successfully.")
                return True
            except:
                print(Fore.YELLOW+"File error in client.")
                file.close()
                return False


        except:
            print(Fore.YELLOW+"Peer is not online.")
            serv.close()
            return False


def run():
    print(Fore.GREEN+"Press cntl + C whenever you want to exit")
    server_connection = ServerConnection()
    status = server_connection.connect()
    if status is False:
        return

    client = ClientSession()

    # setting name and address in server DB
    while True:
        print(Fore.GREEN+"Please enter your unique username:")
        username = input(Fore.WHITE)
        status = server_connection.post_user_data(username, client.ip, client.welcome_port)
        if status is True:
            client.name = username
            break
        elif status is False:
            return


    # now we can initialize client's welcome thread
    client.initialize()

    # getting list of users
    while True:
        users = server_connection.get_list()
        if users is False:
            return
        elif users == "no_user_yet":
            print(Fore.GREEN+"Press U to update users or any other key to exit")
            command = input(Fore.WHITE)
            if command != "U":
                return
        else:
            for name in users:
                print(Fore.BLUE+name)
            break

    # getting user data:
    while True:
        print(Fore.GREEN+"Please enter the name of the user you want to get files from:")
        target_name = input(Fore.WHITE)
        if target_name == client.name:
            print(Fore.GREEN+"You cannot get files from yourself.")
        else:
            user_data = server_connection.get_user_data(target_name)
            if user_data is False:
                return
            elif user_data is None:
                pass
            else:
                target_ip = user_data["ip"]
                target_port = user_data["port"]
                break

    # getting text file or image file
    while True:
        print(Fore.GREEN+"Enter I to get image file or T to get text file:")
        s = input(Fore.WHITE)
        if s == 'I':
            client.req_img(target_ip, target_port)
            return
        elif s == 'T':
            client.req_txt(target_ip, target_port)
            return
        else:
            print(Fore.GREEN+"Invalid command.")


if __name__ == "__main__":
    run()
    
    
