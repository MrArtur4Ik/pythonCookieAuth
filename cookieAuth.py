from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
import posixpath, os, time
import urllib.parse

accounts = {"admin": "admin", "root": "123456"}
#
#Sessions:
#{
# "sessionID": {
#  "user": "USERNAME",
#  "timestamp": float
# }
#}
#
sessions = {}

def translate_path(path):
	path = path.split('?', 1)[0]
	path = path.split('#', 1)[0]
	try:
		path = urllib.parse.unquote(path, errors='surrogatepass')
	except UnicodeDecodeError:
		path = urllib.parse.unquote(path)
	path = posixpath.normpath(path)
	return path

def parse_cookie(s):
	cookie = SimpleCookie()
	cookie.load(s)
	return {k: v.value for k, v in cookie.items()}

def get_session(cookie: dict):
	return sessions[cookie["psessionid"]] if "psessionid" in cookie else None

class ServerHandler(BaseHTTPRequestHandler):
	server_version = "PythonCookie test"
	params = {}

	auth_form = """
	<h2>Авторизация</h2>
	<form action="login" method="post">
	Логин: <br><input type="text" name="user"><br>
	Пароль: <br><input type="password" name="password"><br><br>
	<input type="submit" value="Войти">
	</form>
	"""
	
	def do_POST(self):
		if "Content-Length" in self.headers and "Content-Type" in self.headers:
			if self.headers["Content-Type"] == "application/x-www-form-urlencoded":
				rawtext = self.rfile.read(int(self.headers["Content-Length"])).decode()
				params = urllib.parse.parse_qsl(rawtext)
				self.params = dict(params)
		self.do_GET()

	def do_GET(self):
		path = translate_path(self.path)
		
		content = b''
		if path == "/":
			self.send_response(200)
			self.send_header("Content-type", "text/html; charset=utf-8")
			cookie = {}
			if "Cookie" in self.headers:
				cookie = parse_cookie(self.headers["Cookie"])
			session = get_session(cookie)
			if session:
				user = session["user"]
				content += f'Вы вошли в аккаунт {user}!<br>'.encode()
				content += f'<a href="logout">Выйти из аккаунта</a>'.encode()
			else:
				content += self.auth_form.encode()
		elif path == "/login":
			if self.command == "POST":
				self.send_response(302)
				self.send_header("Location", "/")
				if "user" in self.params and "password" in self.params:
					user = self.params["user"]
					password = self.params["password"]
					if user in accounts and accounts[user] == password:
						sessionid = os.urandom(16).hex()
						sessions[sessionid] = {
							"user": user,
							"timestamp": time.time()
						}
						self.send_header("Set-Cookie", f'psessionid={sessionid}')
				self.end_headers()
			else:
				self.send_response(200)
				self.send_header("Content-type", "text/html; charset=utf-8")
				content += "Используйте POST запрос для авторизации!".encode()
		elif path == "/logout":
			cookie = {}
			if "Cookie" in self.headers:
				cookie = parse_cookie(self.headers["Cookie"])
			if "psessionid" in cookie and cookie["psessionid"] in sessions:
				del sessions[cookie["psessionid"]]
			self.send_response(302)
			self.send_header("Location", "/")
			self.send_header("Set-Cookie", f'psessionid=0; Max-Age=0')
			self.end_headers()
			return
		else:
			self.send_response(404)
			self.send_header("Content-type", "text/html; charset=utf-8")
			content += "Ресурс не найден!".encode()
		self.send_header("Content-Length", str(len(content)))
		self.end_headers()
		self.wfile.write(content)

if __name__ == "__main__":
	server = ThreadingHTTPServer(("", 8081), ServerHandler)
	server.serve_forever()
