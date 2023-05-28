from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import redis
import socket

server_ip = '127.0.0.1'
server_port = 8000
redis_ip = '127.0.0.1'
redis_port = 6379

r = redis.Redis(host=redis_ip, port=redis_port, db=1)


def register_user(name, ip, port):
    if r.exists(name) != 0:
        return False
    else:
        d = {"ip": ip, "port": port}
        j = json.dumps(d)
        r.set(name, j)
        return True


def get_user_data(name):
    j = r.get(name)
    return j


def get_list():
    list_users = r.keys()
    if list_users is None:
        return None
    list_users=[x.decode('utf-8') for x in list_users]
    j = json.dumps(list_users)
    return j


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == 'list':
            list_users = get_list()
            if list_users is not None:
                data = list_users.encode('utf-8')
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            else:
                self.send_response(400)
                self.end_headers()
                return

        elif self.path.startswith('user'):
            target_user_name = self.path[5:]
            user_data = get_user_data(target_user_name)
            if user_data is not None:
                data = user_data
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            else:
                self.send_response(400)
                self.end_headers()
                return

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        user_data = json.loads(post_body.decode('utf-8'))
        name = user_data["name"]
        ip = user_data["ip"]
        port = user_data["port"]
        successful_register = register_user(name, ip, port)
        if successful_register:
            self.send_response(200)
            self.end_headers()
            return
        else:
            self.send_response(400)
            self.end_headers()
            return


def run(server_class=HTTPServer, handler_class=Handler):
    server_address = (server_ip, server_port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


if __name__ == "__main__":
    print(server_ip)
    run()
