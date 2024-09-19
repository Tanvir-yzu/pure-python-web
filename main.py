import http.server
import socketserver
from http import HTTPStatus
import urllib.parse
import sqlite3
from colorama import Fore, Style

PORT = 8080
DATABASE = 'todo.db'

def create_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # Create tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            completed BOOLEAN NOT NULL DEFAULT 0,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # Check if the user is logged in
            cookie_header = self.headers.get('Cookie')
            username = self.get_username_from_cookie(cookie_header)
            if username:
                self.show_todo_list(username)
            else:
                self.redirect_to_login()
        elif self.path == '/login':
            self.show_login_page()
        elif self.path == '/register':
            self.show_register_page()
        elif self.path.startswith('/delete'):
            self.delete_task()
        elif self.path.startswith('/complete'):
            self.complete_task()
        elif self.path == '/logout':
            self.handle_logout()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Page not found")

    def do_POST(self):
        if self.path == '/login':
            self.handle_login()
        elif self.path == '/register':
            self.handle_registration()
        elif self.path == '/add':
            # Add a new task if the user is logged in
            cookie_header = self.headers.get('Cookie')
            username = self.get_username_from_cookie(cookie_header)
            if username:
                self.add_task(username)
            else:
                self.redirect_to_login()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Page not found")

    def show_login_page(self):
        """Displays the login page."""
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Login</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="flex items-center justify-center h-screen bg-gray-100">
                <div class="max-w-md w-full bg-white rounded-lg shadow-md p-8">
                    <h2 class="text-2xl font-bold mb-6">Login</h2>
                    <form method="POST" action="/login">
                        <label for="username" class="block text-sm font-medium text-gray-700">Username:</label>
                        <input type="text" id="username" name="username" class="border border-gray-300 rounded-md p-2 w-full mb-4" required>
                        
                        <label for="password" class="block text-sm font-medium text-gray-700">Password:</label>
                        <input type="password" id="password" name="password" class="border border-gray-300 rounded-md p-2 w-full mb-6" required>
                        
                        <input type="submit" value="Login" class="w-full bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600">
                    </form>
                    <p class="mt-4">Don't have an account? <a href="/register" class="text-blue-500">Register</a></p>
                </div>
            </body>
            </html>
        ''')

    def show_register_page(self):
        """Displays the registration page."""
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Register</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="flex items-center justify-center h-screen bg-gray-100">
                <div class="max-w-md w-full bg-white rounded-lg shadow-md p-8">
                    <h2 class="text-2xl font-bold mb-6">Register</h2>
                    <form method="POST" action="/register">
                        <label for="username" class="block text-sm font-medium text-gray-700">Username:</label>
                        <input type="text" id="username" name="username" class="border border-gray-300 rounded-md p-2 w-full mb-4" required>
                        
                        <label for="email" class="block text-sm font-medium text-gray-700">Email:</label>
                        <input type="email" id="email" name="email" class="border border-gray-300 rounded-md p-2 w-full mb-4" required>
                        
                        <label for="password" class="block text-sm font-medium text-gray-700">Password:</label>
                        <input type="password" id="password" name="password" class="border border-gray-300 rounded-md p-2 w-full mb-6" required>
                        
                        <input type="submit" value="Register" class="w-full bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600">
                    </form>
                    <p class="mt-4">Already have an account? <a href="/login" class="text-blue-500">Login</a></p>
                </div>
            </body>
            </html>
        ''')

    def handle_registration(self):
        """Handles user registration."""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = urllib.parse.parse_qs(post_data.decode('utf-8'))

        username = data.get('username', [''])[0]
        email = data.get('email', [''])[0]
        password = data.get('password', [''])[0]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', (username, email, password))
            conn.commit()
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header('Location', '/login')
            self.end_headers()
        except sqlite3.IntegrityError:
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header('Location', '/register')
            self.end_headers()
        finally:
            conn.close()

    def handle_login(self):
        """Handles user login."""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = urllib.parse.parse_qs(post_data.decode('utf-8'))

        username = data.get('username', [''])[0]
        password = data.get('password', [''])[0]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header('Set-Cookie', f'username={username}; Path=/')
            self.send_header('Location', '/')
            self.end_headers()
        else:
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header('Location', '/login')
            self.end_headers()

    def get_username_from_cookie(self, cookie_header):
        """Extracts the username from cookies."""
        if cookie_header:
            cookies = cookie_header.split(';')
            for cookie in cookies:
                name, value = cookie.strip().split('=')
                if name == 'username':
                    return value
        return None

    def redirect_to_login(self):
        """Redirects to the login page."""
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header('Location', '/login')
        self.end_headers()

    def show_todo_list(self, username):
        """Displays the to-do list for the logged-in user."""
        # Fetch user ID from the database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username=?', (username,))
        user = cursor.fetchone()
        if not user:
            self.redirect_to_login()
            return

        user_id = user[0]

        # Fetch tasks for the user
        cursor.execute('SELECT id, task, completed FROM tasks WHERE user_id=?', (user_id,))
        tasks = cursor.fetchall()
        conn.close()

        # Render the to-do list page
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>To-Do List</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="flex items-center justify-center h-screen bg-gray-100">
                <div class="max-w-md w-full bg-white rounded-lg shadow-md p-8">
                    <h2 class="text-2xl font-bold mb-6">To-Do List for {username}</h2>
                    <form method="POST" action="/add">
                        <input type="text" name="task" placeholder="New task" class="border border-gray-300 rounded-md p-2 w-full mb-4" required>
                        <input type="submit" value="Add Task" class="w-full bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 mb-4">
                    </form>
                    <ul class="list-disc pl-5">
        ''')

        # List all tasks
        for task in tasks:
            task_id, task_text, completed = task
            self.wfile.write(f'<li class="mb-2{" line-through" if completed else ""}">'.encode('utf-8'))
            self.wfile.write(f'{task_text} '.encode('utf-8'))
            self.wfile.write(f'''
                <a href="/delete?id={task_id}" class="text-red-500 ml-2">Delete</a>
                <a href="/complete?id={task_id}" class="text-green-500 ml-2">{"Undo" if completed else "Complete"}</a>
            </li>
            '''.encode('utf-8'))

        # Log Out Button
        self.wfile.write(f'''
                    </ul>
                    <form method="GET" action="/logout">
                        <input type="submit" value="Log Out" class="w-full bg-red-500 text-white px-4 py-2 rounded-md hover:bg-red-600 mt-4">
                    </form>
                </div>
            </body>
            </html>
        ''')

    def add_task(self, username):
        """Adds a new task for the logged-in user."""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = urllib.parse.parse_qs(post_data.decode('utf-8'))
        task_text = data.get('task', [''])[0]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username=?', (username,))
        user = cursor.fetchone()
        if user:
            user_id = user[0]
            cursor.execute('INSERT INTO tasks (task, user_id) VALUES (?, ?)', (task_text, user_id))
            conn.commit()
        conn.close()

        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header('Location', '/')
        self.end_headers()

    def delete_task(self):
        """Deletes a task based on the ID."""
        query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        task_id = query_components.get('id', [''])[0]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id=?', (task_id,))
        conn.commit()
        conn.close()

        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header('Location', '/')
        self.end_headers()

    def complete_task(self):
        """Marks a task as completed or uncompleted based on the ID."""
        query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        task_id = query_components.get('id', [''])[0]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('UPDATE tasks SET completed = NOT completed WHERE id=?', (task_id,))
        conn.commit()
        conn.close()

        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header('Location', '/')
        self.end_headers()

    def handle_logout(self):
        """Handles user log out by clearing the cookie."""
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header('Set-Cookie', 'username=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/')
        self.send_header('Location', '/login')
        self.end_headers()

if __name__ == '__main__':
    create_database()
    with socketserver.TCPServer(("", PORT), Handler, False) as httpd:
        print(f"{Fore.YELLOW}Server started at port {PORT}{Style.RESET_ALL}")
        httpd.allow_reuse_address = True
        httpd.server_bind()
        httpd.server_activate()
        httpd.serve_forever()
