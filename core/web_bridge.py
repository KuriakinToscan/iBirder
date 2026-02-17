import http.server
import socketserver
import threading
import time
import os
import sys

class ImageHandler(http.server.BaseHTTPRequestHandler):
    target_image_path = None
    
    def do_GET(self):
        if self.path != '/foto.jpg':
            self.send_error(404, "Not Found")
            return

        if not self.target_image_path or not os.path.exists(self.target_image_path):
            self.send_error(404, "Image not found")
            return
            
        try:
            with open(self.target_image_path, 'rb') as f:
                content = f.read()
                
            self.send_response(200)
            self.send_header('Content-type', 'image/jpeg')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Access-Control-Allow-Origin', '*') # CORS friendly
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, str(e))
            
    def log_message(self, format, *args):
        # Silenciar logs do servidor para não sujar o terminal do usuário
        return

class GoogleLensBridge:
    def __init__(self, port=5800):
        self.port = port
        self.server = None
        self.thread = None
        
    def start(self, image_path, timeout=30):
        """
        Inicia o servidor em uma thread separada servindo a imagem no path especificado.
        O servidor será encerrado automaticamente após 'timeout' segundos.
        """
        # Configura o path estático na classe handler
        ImageHandler.target_image_path = image_path
        
        # Cria o servidor
        # allow_reuse_address ajuda a evitar erro de "Address already in use" se reiniciar rápido
        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("", self.port), ImageHandler)
        
        # Inicia thread
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        
        # Agenda desligamento
        shutdown_timer = threading.Timer(timeout, self.stop)
        shutdown_timer.daemon = True
        shutdown_timer.start()
        
        return f"http://localhost:{self.port}/foto.jpg"

    def stop(self):
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except:
                pass
            self.server = None
