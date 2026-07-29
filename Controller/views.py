from flask import render_template

def init_routes(app):
    @app.route('/')
    def home():
        return render_template('home.html') 
    
    @app.route('/sispy')
    def sispy_page():
        return render_template('index.old.html')
