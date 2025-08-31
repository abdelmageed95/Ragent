"""
Fallback HTML templates when Jinja2 templates are not available
"""

def get_register_html():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Register - AI System</title></head>
    <body>
        <h1>Register</h1>
        <form method="post">
            <input name="username" placeholder="Username" required>
            <input name="email" type="email" placeholder="Email" required>
            <input name="password" type="password" placeholder="Password" required>
            <input name="full_name" placeholder="Full Name">
            <button type="submit">Register</button>
        </form>
        <a href="/login">Already have an account? Login</a>
    </body>
    </html>
    """

def get_login_html():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Login - AI System</title></head>
    <body>
        <h1>Login</h1>
        <form method="post">
            <input name="email" type="email" placeholder="Email" required>
            <input name="password" type="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <a href="/register">Don't have an account? Register</a>
    </body>
    </html>
    """

def get_dashboard_html(user):
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Dashboard - AI System</title></head>
    <body>
        <h1>Welcome, {user['username']}!</h1>
        <p>MongoDB backend is running. Save templates to templates/ directory for full UI.</p>
        <form method="post" action="/logout">
            <button type="submit">Logout</button>
        </form>
    </body>
    </html>
    """

def get_chat_html():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Chat - AI System</title></head>
    <body>
        <h1>Chat Interface</h1>
        <p>MongoDB backend is running. Save templates to templates/ directory for full UI.</p>
        <a href="/dashboard">Back to Dashboard</a>
    </body>
    </html>
    """