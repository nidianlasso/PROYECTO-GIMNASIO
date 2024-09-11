from flask import Flask, render_template
import os

templateDir= os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
templateDir = os.path.join(templateDir, 'src','templates')

app = Flask(__name__, template_folder=templateDir)

#ARCHIVO HTML QUE SE LLAMA
@app.route('/')
def login():
    return render_template('login.html')



#para lanzar la aplicacion
if __name__ == '__main__':
    app.run(debug=True, port=4000)